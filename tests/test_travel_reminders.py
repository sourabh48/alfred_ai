"""Explicit local consent and atomic in-app delivery; synthetic trips only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from django.db import close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError

from apps.mobility.models import TravelPlan, TravelPlanningSession
from apps.mobility.services.travel import reminders
from apps.mobility.services.travel.editor import EditConflict
from apps.mobility.services.travel_conversation import new_session, save_plan, send_message
from tests import test_travel_packing as packing_fixtures

NOW = datetime(2035, 1, 1, 0, 0, tzinfo=timezone.utc)


class TravelReminderTests(TestCase):
    def setUp(self):
        packing_fixtures.TravelPackingTests.setUp(self)
        self.clock=self.enterContext(patch.object(reminders,'current_time',return_value=NOW))

    def policy(self):
        result=self.client.get(self.url)
        self.assertEqual(result.status_code,200,result.content)
        return result.json()['travel_reminders']

    def change(self, kind, **fields):
        data=dict(action='reminders',operation=kind,request_id=str(uuid4()),reminder_revision=self.policy()['revision'])|fields
        return self.client.post(self.url,data,content_type='application/json')

    def enabled(self):
        response=self.change('consent',enabled=True)
        self.assertEqual(response.status_code,200,response.content)

    def create(self, **fields):
        return self.change('create',**(dict(reminder_id=str(uuid4()),label='Synthetic pack before travel',zone='Asia/Kolkata',local_time='2035-01-02T10:00')|fields))

    def scheduled(self):
        self.enabled();result=self.create()
        self.assertEqual(result.status_code,200,result.content)
        return self.policy()['reminders'][0]

    def test_default_off_requires_explicit_consent_and_is_per_trip(self):
        self.assertFalse(self.policy()['enabled'])
        self.assertNotIn(reminders.KEY,TravelPlan.objects.get(pk=self.session.plan_id).planning_state)
        self.assertEqual(reminders.sweep_due()['processed'],0)
        self.assertEqual(self.create().status_code,400)
        self.enabled()
        other=new_session(self.user);save_plan(other,draft=True);other.refresh_from_db()
        self.assertFalse(self.client.get(f'/api/mobility/planner/sessions/{other.pk}/').json()['travel_reminders']['enabled'])
        self.assertEqual(self.client.get(self.url)['Cache-Control'],'no-store, private')

    def test_create_edit_cancel_reschedule_and_optout_do_not_revive_old_occurrences(self):
        row=self.scheduled()
        self.assertEqual(row['due_at'],'2035-01-02T04:30:00+00:00')
        self.assertEqual(self.change('edit',reminder_id=row['id'],label='Synthetic corrected item',zone='UTC',local_time='2035-01-03T10:00').status_code,200)
        self.assertNotEqual(self.policy()['reminders'][0]['occurrence_id'],row['occurrence_id'])
        self.assertEqual(self.change('cancel',reminder_id=row['id']).status_code,200)
        self.assertEqual(self.policy()['reminders'][0]['status'],'cancelled')
        self.assertEqual(self.change('reschedule',reminder_id=row['id'],label='Synthetic new occurrence',zone='UTC',local_time='2035-01-04T10:00').status_code,200)
        self.assertEqual(self.change('consent',enabled=False).status_code,200)
        self.enabled()
        self.clock.return_value=NOW+timedelta(days=10)
        self.assertEqual(reminders.deliver_due(self.session.plan_id),0)
        self.assertEqual(self.policy()['reminders'][0]['status'],'cancelled')

    def test_dst_gaps_folds_and_iana_utc_conversion(self):
        with self.assertRaises(ValidationError):reminders.schedule('America/New_York','2026-03-08T02:30')
        with self.assertRaises(ValidationError):reminders.schedule('America/New_York','2026-11-01T01:30')
        self.assertEqual(reminders.schedule('America/New_York','2026-11-01T01:30',0),('2026-11-01T05:30:00+00:00',0))
        self.assertEqual(reminders.schedule('America/New_York','2026-11-01T01:30',1),('2026-11-01T06:30:00+00:00',1))
        self.assertEqual(reminders.schedule('Asia/Kolkata','2035-01-02T10:00')[0],'2035-01-02T04:30:00+00:00')
        with self.assertRaises(ValueError):reminders._stamp(datetime(2035,1,1))

    def test_stale_nonce_replay_and_conflicting_nonce_are_safe(self):
        self.enabled()
        data=dict(action='reminders',operation='create',request_id=str(uuid4()),reminder_revision=self.policy()['revision'],reminder_id=str(uuid4()),label='Synthetic retry',zone='UTC',local_time='2035-01-02T10:00')
        first=self.client.post(self.url,data,content_type='application/json')
        self.assertEqual(first.status_code,200,first.content)
        revision=self.policy()['revision']
        self.assertEqual(self.client.post(self.url,data,content_type='application/json').status_code,200)
        self.assertEqual(self.policy()['revision'],revision)
        self.assertEqual(self.client.post(self.url,data|{'label':'Changed nonce'},content_type='application/json').status_code,409)
        self.assertEqual(self.change('consent',enabled=False,reminder_revision=0).status_code,409)
        self.assertEqual(len(self.policy()['reminders']),1)

    def test_deliver_once_late_after_downtime_and_reschedule_new_occurrence(self):
        row=self.scheduled()
        self.clock.return_value=datetime.fromisoformat(row['due_at'])+timedelta(hours=3)
        self.assertEqual(reminders.sweep_due()['refreshed'],1)
        self.assertEqual(reminders.sweep_due()['refreshed'],0)
        delivery=self.policy()['deliveries'][0]
        self.assertTrue(delivery['late'])
        self.assertEqual(delivery['occurrence_id'],row['occurrence_id'])
        self.assertEqual(self.change('reschedule',reminder_id=row['id'],label=row['label'],zone='UTC',local_time='2035-01-03T10:00').status_code,200)
        next_row=self.policy()['reminders'][0]
        self.clock.return_value=datetime.fromisoformat(next_row['due_at'])
        self.assertEqual(reminders.deliver_due(self.session.plan_id),1)
        self.assertEqual(reminders.deliver_due(self.session.plan_id),0)
        self.assertEqual(len(self.policy()['deliveries']),2)
        self.assertFalse(self.policy()['deliveries'][-1]['late'])

    def test_completed_cancelled_and_reopened_trips_never_revive_pending_delivery(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        plan.destination='Synthetic trip';plan.start_date=NOW.date();plan.end_date=(NOW+timedelta(days=2)).date()
        plan.save(update_fields=['destination','start_date','end_date'])
        for status in ('completed','cancelled'):
            with self.subTest(status=status):
                if status=='cancelled':
                    self.client.patch(f'/api/mobility/travel-plans/{self.session.plan_id}/',{'status':'draft'},content_type='application/json')
                row=self.scheduled() if status=='completed' else None
                response=self.client.patch(f'/api/mobility/travel-plans/{self.session.plan_id}/',{'status':status},content_type='application/json')
                self.assertEqual(response.status_code,200,response.content)
                self.assertFalse(self.policy()['enabled'])
                self.assertEqual(self.create().status_code,400)
                self.assertEqual(reminders.deliver_due(self.session.plan_id,NOW+timedelta(days=10)),0)
        self.assertEqual(self.policy()['deliveries'],[])

    def test_malformed_fields_future_time_and_caps_are_bounded(self):
        self.enabled()
        for fields in ({'zone':'../private'},{'zone':[]},{'fold':True},{'fold':2},{'label':[]},{'local_time':'2035-01-02T10:00Z'},{'local_time':'2000-01-01T00:00'},{'extra':'forbidden'},{'operation':[]},{'operation':{}},{'enabled':'yes'}):
            with self.subTest(fields=fields):self.assertEqual(self.create(**fields).status_code,400)
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        with patch.object(reminders,'LIMIT',1):
            self.assertEqual(self.create().status_code,200)
            self.assertEqual(self.create().status_code,400)
        self.assertEqual(len(self.policy()['reminders']),1)

    def test_auth_owner_csrf_and_corrupt_data_fail_closed_without_disclosure(self):
        row=self.scheduled()
        secured=Client(enforce_csrf_checks=True);secured.force_login(self.user)
        self.assertEqual(secured.post(self.url,{'action':'reminders'},content_type='application/json').status_code,403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.client.post(self.url,{'action':'reminders'},content_type='application/json').status_code,404)
        self.client.logout();self.assertIn(self.client.get(self.url).status_code,(401,403));self.client.force_login(self.user)
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        original=deepcopy(plan.planning_state)
        for damaged in (dict(enabled='true'),dict(revision=True),dict(reminders=[{'private':'Synthetic private path'}]),dict(next_due_at='2000-01-01T00:00:00+00:00')):
            with self.subTest(damaged=damaged):
                plan.planning_state=deepcopy(original);plan.planning_state[reminders.KEY].update(damaged);plan.save(update_fields=['planning_state'])
                response=self.client.get(self.url)
                self.assertEqual(response.status_code,503)
                self.assertNotIn('Synthetic private path',response.content.decode())
                with self.assertRaises(reminders.RemindersUnavailable):reminders.deliver_due(plan.pk,NOW+timedelta(days=5))
                plan.refresh_from_db();self.assertEqual(plan.planning_state[reminders.KEY]['deliveries'],[])

    def test_preserves_packing_and_private_documents_across_save_and_new_session(self):
        from apps.mobility.services.travel.packing import update_packing
        from apps.mobility.services.travel_discovery import fact
        from apps.mobility.services.travel_itinerary import build_multi_stop_itinerary
        from apps.mobility.services.travel.editor import apply_edit,editor_payload
        from tests.test_travel_candidate_pool import synthetic_pool
        row=self.scheduled()
        self.enterContext(patch('apps.mobility.services.travel.documents.catalog',return_value={}))
        update_packing(self.session,dict(action='packing',operation='add',item_id=str(uuid4()),label='Synthetic durable packing',checklist_revision=0))
        packing=TravelPlan.objects.get(pk=self.session.plan_id).planning_state.copy()
        self.session.refresh_from_db()
        self.session.state.update({k:fact(v) for k,v in dict(origin='Bengaluru',trip_duration=4,budget=15000,transport_mode='ride',
            available_start_date='2035-01-02',available_end_date='2035-01-05').items()})
        stops=synthetic_pool(self.user,self.session.state)[:2]
        self.session.state['_itinerary_stops']=fact(stops)
        self.session.state['_itinerary_documents']=fact([dict(id='a'*32,fingerprint='1'*64)])
        self.session.itinerary=build_multi_stop_itinerary(self.session.state,stops)
        self.session.state['owner_note']={'value':'Synthetic retained note'};self.session.save()
        prepared,_=editor_payload(self.session)
        apply_edit(self.session,dict(operation='add',revision=self.session.revision,request_id=str(uuid4()),day_id=prepared['days'][0]['id'],fields={'title':'Synthetic reminder-safe visit'}))
        apply_edit(self.session,dict(operation='undo',revision=self.session.revision,request_id=str(uuid4())))
        _,meta=editor_payload(self.session)
        apply_edit(self.session,dict(operation='order_stops',revision=self.session.revision,request_id=str(uuid4()),stops=[s['id'] for s in reversed(meta['stops'])]))
        save_plan(self.session,draft=True)
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        self.assertEqual(plan.planning_state[reminders.KEY],packing[reminders.KEY])
        self.assertEqual(plan.planning_state['_packing_checklist'],packing['_packing_checklist'])
        self.assertEqual(plan.planning_state['_itinerary_documents'],self.session.state['_itinerary_documents'])
        self.session.delete();reopened=new_session(self.user,plan)
        self.assertNotIn(reminders.KEY,reopened.state)
        self.assertEqual(reminders.reminder_payload(reopened)['reminders'][0]['id'],row['id'])
        clone=new_session(self.user);clone=send_message(clone.pk,self.user,'Continue previous trip')
        self.assertNotIn(reminders.KEY,clone.state)
        save_plan(clone,draft=True);clone.refresh_from_db()
        self.assertFalse(reminders.reminder_payload(clone)['enabled'])

    def test_failed_cas_and_crash_before_commit_roll_back_delivery(self):
        row=self.scheduled();before=self.policy()
        with patch('django.db.models.query.QuerySet.update',return_value=0),self.assertRaises(EditConflict):
            reminders.deliver_due(self.session.plan_id,NOW+timedelta(days=5))
        self.assertEqual(self.policy(),before)
        actual=reminders._save
        def interrupted(*args):
            actual(*args);raise RuntimeError('Synthetic interruption before commit')
        with patch.object(reminders,'_save',side_effect=interrupted),self.assertRaises(RuntimeError):
            reminders.deliver_due(self.session.plan_id,NOW+timedelta(days=5))
        self.assertEqual(self.policy(),before)
        self.assertEqual(reminders.deliver_due(self.session.plan_id,NOW+timedelta(days=5)),1)

    def test_delivery_history_cap_retains_records_and_rejects_another_occurrence(self):
        with patch.object(reminders,'DELIVERY_LIMIT',1):
            row=self.scheduled()
            self.assertEqual(reminders.deliver_due(self.session.plan_id,NOW+timedelta(days=5)),1)
            self.assertEqual(self.change('reschedule',reminder_id=row['id'],label=row['label'],zone='UTC',local_time='2035-02-01T12:00').status_code,400)
            self.assertEqual(len(self.policy()['deliveries']),1)

    def test_due_query_skips_future_trips_and_closed_worker_path_cancels(self):
        row=self.scheduled()
        self.assertEqual(reminders.sweep_due()['processed'],0)
        TravelPlan.objects.filter(pk=self.session.plan_id).update(status='completed')
        self.assertEqual(reminders.sweep_due()['processed'],1)
        self.assertFalse(self.policy()['enabled'])
        self.assertEqual(self.policy()['reminders'][0]['status'],'cancelled')
        self.assertEqual(self.policy()['deliveries'],[])

    def test_delivery_timestamp_is_taken_after_lock_wait_not_sweep_start(self):
        row=self.scheduled();due=datetime.fromisoformat(row['due_at'])
        self.clock.side_effect=[due,due+timedelta(minutes=5),due+timedelta(minutes=5),due+timedelta(minutes=5)]
        self.assertEqual(reminders.sweep_due()['refreshed'],1)
        self.clock.side_effect=None
        delivery=self.policy()['deliveries'][0]
        self.assertTrue(delivery['late'])
        self.assertEqual(delivery['delivered_at'],(due+timedelta(minutes=5)).isoformat())

    def test_corrupt_prefix_does_not_starve_later_valid_due_plans(self):
        row=self.scheduled()
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        for _ in range(100):
            broken=TravelPlan.objects.create(user=self.user,title='Synthetic corrupt schedule',status='draft',planning_state=deepcopy(plan.planning_state))
            broken.planning_state[reminders.KEY]['revision']='corrupt'
            broken.save(update_fields=['planning_state'])
        valid=TravelPlan.objects.create(user=self.user,title='Synthetic later due trip',status='draft',planning_state=deepcopy(plan.planning_state))
        TravelPlan.objects.filter(pk=plan.pk).delete()
        self.clock.return_value=NOW+timedelta(days=5)
        self.assertEqual(reminders.sweep_due(),dict(processed=100,refreshed=0,failed=100))
        self.assertEqual(reminders.sweep_due()['refreshed'],1)
        valid.refresh_from_db();self.assertEqual(len(valid.planning_state[reminders.KEY]['deliveries']),1)
        self.assertEqual(reminders.sweep_due()['refreshed'],0)

    def test_optional_cursor_cache_outages_do_not_block_or_duplicate_delivery(self):
        import sqlite3
        from diskcache import Timeout
        self.enabled()
        for failure in (OSError('Synthetic cursor unavailable'),sqlite3.OperationalError('Synthetic cursor I/O'),Timeout('Synthetic cache timeout')):
            with self.subTest(failure=type(failure).__name__):
                self.clock.return_value=NOW
                self.assertEqual(self.create().status_code,200)
                self.clock.return_value=NOW+timedelta(days=5)
                with patch.object(reminders.cache,'get',side_effect=failure),patch.object(reminders.cache,'set',side_effect=failure):
                    self.assertEqual(reminders.sweep_due()['refreshed'],1)
                    self.assertEqual(reminders.sweep_due()['refreshed'],0)
        self.assertEqual(len(self.policy()['deliveries']),3)


class ReminderDurabilityTests(TransactionTestCase):
    setUp=TravelReminderTests.setUp
    policy=TravelReminderTests.policy
    change=TravelReminderTests.change
    enabled=TravelReminderTests.enabled
    create=TravelReminderTests.create
    scheduled=TravelReminderTests.scheduled

    def _race(self, cancel_first):
        row=self.scheduled();revision=self.policy()['revision']
        entered,release,second_started=Event(),Event(),Event()
        actual=reminders._save
        def held(plan,policy):
            actual(plan,policy)
            entered.set()
            if not release.wait(8):raise AssertionError('Synthetic transaction release timed out')
        cancel=dict(action='reminders',operation='cancel',request_id=str(uuid4()),reminder_revision=revision,reminder_id=row['id'])
        def run(kind,second=False):
            close_old_connections()
            if second:second_started.set()
            try:
                if kind=='cancel':
                    try:reminders.update_reminders(self.session,cancel);return 'cancelled'
                    except EditConflict:return 'conflict'
                return reminders.deliver_due(self.session.plan_id,NOW+timedelta(days=5))
            finally:connection.close()
        with patch.object(reminders,'_save',side_effect=held),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(run,'cancel' if cancel_first else 'deliver')
            try:
                self.assertTrue(entered.wait(8))
                second=pool.submit(run,'deliver' if cancel_first else 'cancel',True)
                self.assertTrue(second_started.wait(8));self.assertFalse(second.done())
            finally:release.set()
            results=(first.result(timeout=12),second.result(timeout=12))
        self.assertEqual(results,('cancelled',0) if cancel_first else (1,'conflict'))
        self.assertEqual(len(self.policy()['deliveries']),0 if cancel_first else 1)

    def test_cancel_wins_concurrent_delivery_without_visible_record(self):self._race(True)

    def test_delivery_wins_concurrent_cancel_with_one_visible_record(self):self._race(False)

    def test_worker_crash_after_commit_replays_actual_native_body_once_after_restart(self):
        row=self.scheduled()
        database=str(connection.settings_dict['NAME'])
        self.assertTrue(Path(database).is_file())
        code='''import ast,os,sys
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
os.environ['DJANGO_SETTINGS_MODULE']='alfred_ai.browser_test_settings'
from django.conf import settings
settings.DATABASES['default']['NAME']=sys.argv[1]
import django
django.setup()
from apps.mobility.services.travel import reminders
from apps.mobility.models import TravelPlan
from alfred_ai.durable_queue import DurableSqliteHuey,REPLAY_SAFE
tree=ast.parse(Path('alfred_ai/native_tasks.py').read_text(encoding='utf-8'))
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='native_travel_reminders')
assert len(node.decorator_list)==1 and ast.unparse(node.decorator_list[0])=="db_periodic_task(crontab(minute='*'))"
node.decorator_list=[]
namespace={'__name__':'alfred_ai.native_tasks'}
exec(compile(ast.Module(body=[node],type_ignores=[]),'native_tasks.py','exec'),namespace)
worker=namespace['native_travel_reminders']
assert worker.__module__+'.'+worker.__name__ in REPLAY_SAFE
queue=DurableSqliteHuey('reminder-restart',filename=sys.argv[3],fsync=True)
task=queue.task()(worker)
at=datetime.fromisoformat(sys.argv[4])+timedelta(hours=2)
with patch.object(reminders,'current_time',return_value=at):
    if sys.argv[2]=='crash':
        task();assert queue.dequeue() is not None
        assert worker()['refreshed']==1
        os._exit(0)
    assert queue.storage.recover(queue.deserialize_task)['requeued']==1
    queue.execute(queue.dequeue())
    assert queue.pending_count()==0
    assert queue.storage.recover(queue.deserialize_task)['requeued']==0
    assert reminders.sweep_due()['refreshed']==0
    policy=TravelPlan.objects.get(pk=int(sys.argv[5])).planning_state[reminders.KEY]
    assert len(policy['deliveries'])==1 and policy['deliveries'][0]['late']
print('native reminder restart replay PASS')
'''
        with TemporaryDirectory() as directory:
            queue=str(Path(directory)/'native-test-jobs.sqlite3')
            for stage in ('crash','replay'):
                result=subprocess.run([sys.executable,'-c',code,database,stage,queue,row['due_at'],str(self.session.plan_id)],capture_output=True,text=True,timeout=45)
                self.assertEqual(result.returncode,0,result.stderr[-1600:])
                if stage=='replay':self.assertIn('restart replay PASS',result.stdout)
        self.assertEqual(len(self.policy()['deliveries']),1)
