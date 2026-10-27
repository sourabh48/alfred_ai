"""Private saved-trip progress, independent of routes, providers and document originals."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.test import Client, TestCase, TransactionTestCase

from apps.mobility.models import TravelPlan, TravelPlanningSession
from apps.mobility.services.travel.packing import KEY, LIMIT, update_packing
from apps.mobility.services.travel.editor import EditConflict
from apps.mobility.services.travel_conversation import new_session, save_plan
from tests import test_travel_planner as fixtures
from tests.travel_persistence_support import durable_fixture_database


class TravelPackingTests(TestCase):
    def setUp(self):
        cache.clear(); self.addCleanup(cache.clear)
        fixtures.TravelPlannerTests.setUp(self)
        self.session = new_session(self.user)
        save_plan(self.session, draft=True)
        self.session.refresh_from_db()
        self.url = f'/api/mobility/planner/sessions/{self.session.pk}/'

    def payload(self):
        return self.client.get(self.url).json()['packing_checklist']

    def change(self, operation, **fields):
        data = dict(action='packing', operation=operation, checklist_revision=self.payload()['revision']) | fields
        return self.client.post(self.url, data, content_type='application/json')

    def test_stable_suggestions_are_read_only_and_unsaved_trip_requires_save(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        plan.transport_mode='ride';plan.save(update_fields=['transport_mode'])
        first = self.payload()
        self.assertIn('Helmet and riding protection', [row['label'] for row in first['items']])
        self.assertEqual(first, self.payload())
        self.assertNotIn(KEY, TravelPlan.objects.get(pk=self.session.plan_id).planning_state)
        self.assertEqual(self.client.get(self.url)['Cache-Control'], 'no-store, private')
        unsaved = new_session(self.user)
        response = self.client.post(f'/api/mobility/planner/sessions/{unsaved.pk}/',
            dict(action='packing', operation='add', checklist_revision=0, item_id=str(uuid4()), label='Synthetic item'), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_crud_complete_uncheck_and_idempotent_retry(self):
        identity = str(uuid4())
        data = dict(item_id=identity, label='  Synthetic   gloves  ', checklist_revision=0)
        first = self.change('add', **data)
        self.assertEqual(first.status_code, 200, first.content)
        revision = first.json()['revision']
        self.assertEqual(self.change('add', **data).json()['revision'], revision)
        self.assertEqual(self.change('update', item_id=identity, label='Synthetic dry gloves', packed=True).status_code, 200)
        self.assertEqual(next(i for i in self.payload()['items'] if i['id']==identity), dict(id=identity,label='Synthetic dry gloves',packed=True))
        self.assertEqual(self.change('update', item_id=identity, packed=False).status_code, 200)
        self.assertEqual(self.change('remove', item_id=identity).status_code, 200)
        old = self.payload()['revision']
        self.assertEqual(self.change('remove', item_id=identity, checklist_revision=0).status_code, 200)
        self.assertEqual(self.payload()['revision'], old)

    def test_stale_conflicts_and_identity_reuse_do_not_overwrite(self):
        item = self.payload()['items'][0]
        self.assertEqual(self.change('update', item_id=item['id'], packed=True).status_code,200)
        before = self.payload()
        self.assertEqual(self.change('update',item_id=item['id'],label='Stale overwrite',checklist_revision=0).status_code,409)
        self.assertEqual(self.change('add',item_id=item['id'],label='Reused identity').status_code,409)
        self.assertEqual(self.payload(),before)

    def test_duplicate_names_limits_and_malformed_input(self):
        first = self.payload()['items'][0]
        self.assertEqual(self.change('add',item_id=str(uuid4()),label='  '+first['label'].upper()+'  ').status_code,400)
        other = self.payload()['items'][1]
        self.assertEqual(self.change('update',item_id=other['id'],label=first['label']).status_code,400)
        for fields in [dict(operation=[]),dict(operation={}),dict(label=''),dict(label='x'*161),dict(label=[]),dict(packed='yes'),dict(checklist_revision=True),dict(item_id='../private'),dict(extra='forbidden')]:
            with self.subTest(fields=fields):
                data=dict(action='packing',operation='update',item_id=first['id'],packed=True,checklist_revision=0)|fields
                self.assertEqual(self.client.post(self.url,data,content_type='application/json').status_code,400)
        self.assertEqual(self.client.post(self.url,[],content_type='application/json').status_code,400)
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        plan.planning_state[KEY]=dict(revision=9,items=[dict(id=str(uuid4()),label=f'Synthetic item {i}',packed=False) for i in range(LIMIT)])
        plan.save(update_fields=['planning_state'])
        self.assertEqual(self.change('add',item_id=str(uuid4()),label='Overflow').status_code,400)
        self.assertEqual(len(self.payload()['items']),LIMIT)

    def test_owner_authentication_and_csrf_isolation(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.client.post(self.url,dict(action='packing'),content_type='application/json').status_code,404)
        self.client.logout()
        self.assertIn(self.client.get(self.url).status_code,(401,403))
        secured=Client(enforce_csrf_checks=True);secured.force_login(self.user)
        self.assertEqual(secured.post(self.url,dict(action='packing'),content_type='application/json').status_code,403)

    def test_save_reopen_and_plan_details_preserve_canonical_checklist(self):
        first=self.payload()['items'][0]
        stale=TravelPlanningSession.objects.get(pk=self.session.pk)
        self.change('update',item_id=first['id'],packed=True)
        before=self.payload()
        save_plan(stale,draft=True)
        self.assertEqual(self.payload(),before)
        response=self.client.patch(f'/api/mobility/travel-plans/{self.session.plan_id}/',
            dict(destination='Synthetic new destination'),content_type='application/json')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(self.payload(),before)
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        self.session.delete()
        reopened=new_session(self.user,plan)
        self.assertNotIn(KEY,reopened.state)
        self.url=f'/api/mobility/planner/sessions/{reopened.pk}/'
        self.assertEqual(self.payload(),before)

    def test_clear_all_does_not_reseed_and_other_trips_are_independent(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        plan.planning_state[KEY]=dict(revision=1,items=[]);plan.save(update_fields=['planning_state'])
        self.assertEqual(self.payload()['items'],[])
        other=new_session(self.user);save_plan(other,draft=True);other.refresh_from_db()
        response=self.client.get(f'/api/mobility/planner/sessions/{other.pk}/')
        self.assertTrue(response.json()['packing_checklist']['items'])
        self.assertNotEqual(other.plan_id,self.session.plan_id)

    def test_compare_and_swap_failure_rolls_back_all_writes(self):
        original=self.payload()
        with patch('django.db.models.query.QuerySet.update',return_value=0),self.assertRaises(EditConflict):
            update_packing(self.session,dict(action='packing',operation='add',item_id=str(uuid4()),label='Synthetic race',checklist_revision=0))
        self.assertEqual(self.payload(),original)

    def test_itinerary_days_stops_undo_and_documents_do_not_reset_packing(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.mobility.services.travel_discovery import fact
        from apps.mobility.services.travel_itinerary import build_multi_stop_itinerary
        from apps.mobility.services.travel.editor import apply_edit, editor_payload
        from tests.test_travel_candidate_pool import synthetic_pool
        self.session.state.update({k:fact(v) for k,v in dict(origin='Bengaluru',trip_duration=4,budget=15000,
            transport_mode='ride',available_start_date=str(timezone.localdate()+timedelta(days=2)),
            available_end_date=str(timezone.localdate()+timedelta(days=5))).items()})
        stops=synthetic_pool(self.user,self.session.state)[:2]
        self.session.state['_itinerary_stops']=fact(stops)
        self.session.itinerary=build_multi_stop_itinerary(self.session.state,stops)
        self.session.save();save_plan(self.session,draft=True)
        item=self.payload()['items'][0]
        self.change('update',item_id=item['id'],packed=True)
        before=self.payload()
        self.session.refresh_from_db()
        self.session.state['_itinerary_documents']=fact([dict(id='a'*32,fingerprint='1'*64)])
        self.session.save()
        prepared,_=editor_payload(self.session)
        apply_edit(self.session,dict(operation='add',revision=self.session.revision,request_id=str(uuid4()),
            day_id=prepared['days'][0]['id'],fields={'title':'Synthetic new activity'}))
        apply_edit(self.session,dict(operation='undo',revision=self.session.revision,request_id=str(uuid4())))
        _,meta=editor_payload(self.session)
        apply_edit(self.session,dict(operation='order_stops',revision=self.session.revision,request_id=str(uuid4()),
            stops=[s['id'] for s in reversed(meta['stops'])]))
        save_plan(self.session,draft=True)
        with patch('apps.mobility.services.travel.documents.catalog',return_value={}):
            self.assertEqual(self.payload(),before)
        saved=TravelPlan.objects.get(pk=self.session.plan_id)
        self.assertEqual(saved.planning_state['_itinerary_documents'],self.session.state['_itinerary_documents'])


class PackingRestartTests(TransactionTestCase):
    setUp=TravelPackingTests.setUp
    payload=TravelPackingTests.payload
    change=TravelPackingTests.change

    def test_new_python_process_reads_durable_trip_progress(self):
        item=self.payload()['items'][0]
        self.assertEqual(self.change('update',item_id=item['id'],packed=True).status_code,200)
        code='''import sys, os
os.environ['DJANGO_SETTINGS_MODULE']='alfred_ai.browser_test_settings'
from django.conf import settings
settings.DATABASES['default']['NAME']=sys.argv[1]
import django
django.setup()
from apps.mobility.models import TravelPlan
state=TravelPlan.objects.get(pk=int(sys.argv[2])).planning_state['_packing_checklist']
assert state['revision']==1 and any(i['id']==sys.argv[3] and i['packed'] for i in state['items'])
print('cold-process checklist persistence PASS')
'''
        with durable_fixture_database() as database:
            self.assertTrue(Path(database).is_file())
            result=subprocess.run([sys.executable,'-c',code,database,str(self.session.plan_id),item['id']],capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr[-1200:])
        self.assertIn('persistence PASS',result.stdout)
