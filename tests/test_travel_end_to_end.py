"""One owned synthetic trip through the seven integrated Travel journeys."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone as utc
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from lxml import etree
from pypdf import PdfReader

from alfred_private_storage import private_directory
from apps.expenses.models import BankAccount, Expense
from apps.loans.models import Loan
from apps.mobility.models import TravelPlan, TravelPlanningSession
from apps.mobility.services.travel import reminders
from apps.mobility.services.travel.affordability import FIELDS
from apps.mobility.services.travel_discovery import value
from apps.mobility.services.travel_research import run_research
from scripts.release_validation import environment
from tests import test_travel_planner as planner
from tests import test_travel_affordability as finance
from tests import test_travel_financial_reconciliation as reconciliation
from tests.test_travel_ics_export import parse_calendar
from tests.test_persistent_memory import SyntheticEmbeddings


class TravelEndToEndTests(TestCase):
    def setUp(self):
        cache.clear();self.addCleanup(cache.clear)
        planner.TravelPlannerTests.setUp(self)
        self.directory=Path(self.enterContext(TemporaryDirectory(prefix='alfred-d1-synthetic-')))
        self.root=private_directory(self.directory/'private')
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.root/'vault'),
            ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,ALFRED_MEMORY_OPENAI_AUTHORIZED=False,
            ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALFRED_MEMORY_SYNC_PROVIDER=''))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.journeys=[]
        self.rate_clock=time.time()
        self.enterContext(patch('rest_framework.throttling.SimpleRateThrottle.timer',new=staticmethod(lambda:self.rate_clock)))

    def mark(self, label):
        self.journeys.append(label)
        # Model time between user journeys while retaining the real rate-limit logic.
        self.rate_clock+=90
        path=Path(settings.BASE_DIR)/'artifacts/travel-d1-20261028/backend-journeys.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(dict(passed=self.journeys,platform=os.name,total=7)),encoding='utf-8')

    def post(self, action, **fields):
        self.session.refresh_from_db()
        revision={} if action in ('packing','reminders') else dict(revision=self.session.revision)
        return self.client.post(self.url,dict(action=action)|revision|fields,content_type='application/json')

    def ok(self,response):
        self.assertEqual(response.status_code,200,response.content[:350]);return response.json()

    def reminder(self, operation, **fields):
        policy=self.client.get(self.url).json()['travel_reminders']
        return self.post('reminders',operation=operation,request_id=str(uuid4()),reminder_revision=policy['revision'],**fields)

    def confirmation(self):
        result=finance.TravelAffordabilityTests.confirmation(self)
        for name in FIELDS:
            result[name]['currency']='INR'
        return result

    def scenario(self):
        url=self.url+'savings/'
        context=self.client.get(url).json()
        money=lambda amount:dict(amount=amount,currency='INR',verified=True)
        return dict(revision=context['trip']['revision'],snapshot=context['trip']['snapshot'],confirmation=self.confirmation(),
            savings=dict(source_revision=context['savings_source']['revision'],departure=str(self.today+timedelta(days=2)),
                income_from=str(self.today),income_until=str(self.today+timedelta(days=365)),verified_on=str(self.today),confirmed=True,
                monthly_income=money('3100'),monthly_goals=money('100'),monthly_contribution=money('310'),
                schedules=[dict(id=self.loan.pk,next_due=str(self.today+timedelta(days=1)),final_due='',verified=True)],
                scenarios={name:dict(income_percent=rate,expense_percent='100') for name,rate in
                           (('conservative','75'),('baseline','90'),('optimistic','100'))}))

    def test_seven_integrated_journeys_and_cold_process_delivery_replay(self):
        # Only weather/provider dispatch and embedding generation are synthetic boundaries.
        created=self.client.post('/api/mobility/planner/sessions/',{},content_type='application/json')
        self.assertEqual(created.status_code,201)
        self.session=TravelPlanningSession.objects.get(pk=created.json()['id'])
        self.url=f'/api/mobility/planner/sessions/{self.session.pk}/'
        self.ok(self.post('message',text=f'{self.today+timedelta(days=2)} to {self.today+timedelta(days=5)}. Budget ₹15000. Bike trip, mountains and photography.'))
        self.ok(self.post('message',text='Yes use that'))
        self.session.refresh_from_db();run_research(self.session.research_runs.first().pk);self.session.refresh_from_db()
        names=[row['name'] for row in self.session.candidates[:2]];self.assertEqual(len(names),2)
        self.ok(self.post('itinerary_stops',stops=names));self.ok(self.post('save'))
        self.session.refresh_from_db();plan=self.session.plan
        reopened=self.client.post('/api/mobility/planner/sessions/',dict(plan_id=plan.pk),content_type='application/json')
        self.assertEqual(reopened.json()['id'],self.session.pk)
        self.assertEqual(reopened.json()['itinerary_stops'],names)
        self.assertEqual((plan.transport_mode,plan.budget),('ride',15000))
        self.assertTrue(all(stop['sources'] for stop in plan.itinerary['stops']))
        self.mark('J1 create/save/reopen')

        raw=b'Synthetic private trip reference. No booking is confirmed.'
        uploaded=self.client.post('/api/ai/document-corpus/upload/',dict(file=SimpleUploadedFile('D1 private.txt',raw),consent='true',days='7'))
        original=None
        if os.name=='nt':
            source=self.ok(uploaded)['document']
            choices=self.ok(self.post('trip_documents',operation='list'))['document_choices']
            selected=next(row for row in choices if row['id']==source['id'])
            self.ok(self.post('trip_documents',operation='link',document_id=source['id'],fingerprint=selected['fingerprint']))
            original=selected['original_path'];download=self.client.get(original)
            self.assertEqual(b''.join(download.streaming_content),raw)
            self.ok(self.post('trip_documents',operation='unlink',document_id=source['id']))
            self.assertEqual(b''.join(self.client.get(original).streaming_content),raw)
            self.ok(self.post('trip_documents',operation='link',document_id=source['id'],fingerprint=selected['fingerprint']))
        else:
            self.assertEqual(uploaded.status_code,503)  # Windows user-bound storage fails closed on other platforms.
        self.mark('J3 real encrypted organizer' if original else 'J3 unsupported-platform fail-closed')

        packing=self.client.get(self.url).json()['packing_checklist'];item=packing['items'][0]
        self.ok(self.post('packing',operation='update',checklist_revision=packing['revision'],item_id=item['id'],label='D1 helmet and gloves',packed=True))
        self.assertFalse(self.client.get(self.url).json()['travel_reminders']['enabled'])
        self.ok(self.reminder('consent',enabled=True));identity=str(uuid4())
        self.due=datetime.combine(self.today+timedelta(days=1),datetime.min.time(),tzinfo=utc.utc)
        fields=dict(reminder_id=identity,label='D1 pack before departure',zone='UTC',local_time=self.due.strftime('%Y-%m-%dT%H:%M'))
        self.ok(self.reminder('create',**fields));self.ok(self.reminder('cancel',reminder_id=identity))
        self.ok(self.reminder('reschedule',**fields))
        other=self.client.post('/api/mobility/planner/sessions/',{},content_type='application/json').json()
        other_url=f'/api/mobility/planner/sessions/{other["id"]}/'
        self.ok(self.client.post(other_url,dict(action='save',draft=True),content_type='application/json'))
        self.assertFalse(self.client.get(other_url).json()['travel_reminders']['enabled'])
        self.ok(self.post('itinerary_stops',stops=names[:1]));self.ok(self.post('itinerary_stops',stops=names))
        baseline=self.client.get(self.url).json();day=baseline['itinerary']['days'][0]
        token=str(uuid4());request=dict(operation='add',request_id=token,day_id=day['id'],fields={'title':'D1 owned activity'})
        self.session.refresh_from_db();body=dict(action='itinerary_edit',revision=self.session.revision)|request
        response=self.client.post(self.url,body,content_type='application/json');data=self.ok(response)
        added=data['itinerary']['days'][0]['items'][-1]
        self.assertEqual(self.client.post(self.url,body,content_type='application/json').status_code,200)
        self.assertEqual(sum(i['id']==added['id'] for d in self.client.get(self.url).json()['itinerary']['days'] for i in d['items']),1)
        self.ok(self.post('itinerary_edit',operation='update',request_id=str(uuid4()),day_id=day['id'],item_id=added['id'],fields={'title':'D1 corrected activity'}))
        self.ok(self.post('itinerary_edit',operation='move',request_id=str(uuid4()),day_id=day['id'],item_id=added['id'],before_id=day['items'][0]['id']))
        order=[s['id'] for s in reversed(data['itinerary_editor']['stops'])]
        self.ok(self.post('itinerary_edit',operation='order_stops',request_id=str(uuid4()),stops=order))
        self.ok(self.post('itinerary_edit',operation='remove',request_id=str(uuid4()),day_id=day['id'],item_id=added['id']))
        self.ok(self.post('itinerary_edit',operation='undo',request_id=str(uuid4())))
        current=self.client.get(self.url).json()
        self.assertEqual(current['itinerary']['budget']['status'],'needs_recalculation')
        self.assertEqual(current['itinerary']['route']['confidence'],'UNKNOWN')
        stale=dict(action='itinerary_edit',operation='undo',request_id=str(uuid4()),revision=baseline['revision'])
        self.assertEqual(self.client.post(self.url,stale,content_type='application/json').status_code,409)
        self.ok(self.post('save'));self.session.refresh_from_db();plan.refresh_from_db()
        self.assertEqual(self.client.get(self.url).json()['packing_checklist']['items'][0]['label'],'D1 helmet and gloves')
        self.assertTrue(self.client.get(self.url).json()['packing_checklist']['items'][0]['packed'])
        if original:self.assertEqual(self.client.get(self.url).json()['trip_documents'][0]['status'],'available')
        self.mark('J2 edits/retry/conflict/invalidation');self.mark('J4 packing/reminder consent/lifecycle')

        preview=self.ok(self.post('calendar_preview'));exports={}
        for kind in ('pdf','gpx','ics'):
            response=self.post('export_'+kind,**({'calendar':dict(snapshot=preview['snapshot'],events=[])} if kind=='ics' else {}))
            self.assertEqual(response.status_code,200,response.content[:300]);self.assertEqual(response['Cache-Control'],'no-store, private')
            exports[kind]=response.content
        text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(exports['pdf']),strict=True).pages)
        xml=etree.fromstring(exports['gpx'],etree.XMLParser(resolve_entities=False,no_network=True))
        calendar=parse_calendar(exports['ics'])
        expected=[s['name'] for s in plan.itinerary['stops']]
        self.assertIn(' → '.join(expected),text)
        self.assertEqual(xml.xpath('//*[local-name()="wpt"]/*[local-name()="name"]/text()'),expected)
        self.assertFalse(xml.xpath('//*[local-name()="trk" or local-name()="rte"]'))
        self.assertEqual(calendar['events'][0]['location'],' → '.join(expected));self.assertTrue(calendar['roundtrip'])
        self.assertEqual(calendar['events'][0]['start'],plan.itinerary['days'][0]['date'])
        self.assertNotIn('D1 private',text)
        old_revision=self.session.revision
        self.ok(self.post('itinerary_edit',operation='add',request_id=str(uuid4()),day_id=day['id'],fields={'title':'D1 later change'}))
        for kind in ('pdf','gpx','ics'):
            body=dict(action='export_'+kind,revision=old_revision)
            if kind=='ics':body['calendar']=dict(snapshot=preview['snapshot'],events=[])
            self.assertEqual(self.client.post(self.url,body,content_type='application/json').status_code,409)
        self.ok(self.post('save'));self.mark('J5 consistent independently parsed exports/stale rejection')

        self.user.monthly_income='3100';self.user.rent_or_emi='100';self.user.save()
        BankAccount.objects.create(user=self.user,account_number='D1 synthetic',current_balance='1000',last_synced_at=timezone.now())
        self.expense=Expense.objects.create(user=self.user,amount='50',category='groceries',transaction_date=self.today)
        self.loan=Loan.objects.create(user=self.user,principal='1000',emi='25',remaining_balance='800',interest_rate=0,start_date=self.today)
        scenario=self.scenario();current_url=self.url+'affordability/'
        current_payload={k:v for k,v in scenario.items() if k!='savings'}
        before=reconciliation.TravelFinancialReconciliationTests.snapshot(self)
        current=self.ok(self.client.post(current_url,current_payload,content_type='application/json'))
        future=self.ok(self.client.post(self.url+'savings/',scenario,content_type='application/json'))
        self.assertEqual(current['amounts'],future['current']['amounts']);self.assertEqual(current['amounts']['available_trip_funds'],'525.00')
        self.assertEqual(before,reconciliation.TravelFinancialReconciliationTests.snapshot(self))
        Expense.objects.filter(pk=self.expense.pk).update(amount='51')
        self.assertEqual(self.client.post(self.url+'savings/',scenario,content_type='application/json').status_code,409)
        scenario=self.scenario();self.assertEqual(self.ok(self.client.post(self.url+'savings/',scenario,content_type='application/json'))['current']['amounts']['available_trip_funds'],'524.00')
        self.mark('J6 canonical current/future/source correction/no writes')
        self.session.refresh_from_db();plan.refresh_from_db()
        self.cold_reopen(plan,scenario,raw if original else None)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.client.get(current_url).status_code,404)
        if original:self.assertIn(self.client.get(original).status_code,(403,404))
        self.client.logout();self.assertIn(self.client.get(self.url).status_code,(401,403))
        self.mark('J7 cold reopen/due replay/owner/auth isolation')
        self.assertEqual(len(self.journeys),7)

    def cold_reopen(self,plan,scenario,raw):
        root=private_directory(self.root/'restart');database=root/'synthetic.sqlite3'
        self.assertTrue(connection.in_atomic_block)
        database.write_bytes(connection.connection.serialize())
        (root/'input.json').write_text(json.dumps(dict(scenario=scenario,plan=plan.pk,session=self.session.pk,
            owner=self.user.pk,due=self.due.isoformat(),documents=bool(raw))),encoding='utf-8')
        env=environment(root/'runtime');env.update(DATABASE_URL='sqlite:///'+database.as_posix(),
            D1_VAULT=str(settings.ALFRED_MEMORY_DIR),DJANGO_SECRET_KEY=settings.SECRET_KEY,
            DJANGO_SETTINGS_MODULE='alfred_ai.settings',D1_ROOT=str(root))
        program='''
import json,os
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
import django
django.setup()
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from apps.mobility.models import TravelPlan,TravelPlanningSession
from apps.mobility.services.travel import reminders
from apps.mobility.services.travel.savings import calculate_savings
from apps.mobility.planner_views import session_payload
from tests import test_travel_financial_reconciliation as receipts
root=Path(os.environ['D1_ROOT']).resolve()
assert Path(connection.settings_dict['NAME']).resolve()==root/'synthetic.sqlite3'
vault=Path(os.environ['D1_VAULT']).resolve()
assert vault.is_relative_to(root.parent)
override_settings(ALFRED_MEMORY_DIR=str(vault)).enable()
data=json.loads((root/'input.json').read_text())
user=get_user_model().objects.get(pk=data['owner'])
session=TravelPlanningSession.objects.get(pk=data['session'],user=user)
before=session_payload(session)
canonical=receipts.TravelFinancialReconciliationTests.snapshot(None)
canonical.pop('mobility.TravelPlan');canonical.pop('mobility.TravelPlanningSession')
assert before['packing_checklist']['items'][0]['packed']
assert not data['documents'] or before['trip_documents'][0]['status']=='available'
at=datetime.fromisoformat(data['due'])+timedelta(minutes=10)
with patch.object(reminders,'current_time',return_value=at),patch('requests.sessions.Session.request',side_effect=AssertionError('external request')):
    reminders.sweep_due()
    result=calculate_savings(user,data['scenario']['confirmation'],data['scenario']['savings'])
assert result['scenarios'] is not None
after=session_payload(session)
check=receipts.TravelFinancialReconciliationTests.snapshot(None)
check.pop('mobility.TravelPlan');check.pop('mobility.TravelPlanningSession')
assert canonical==check
assert len(after['travel_reminders']['deliveries'])==1
assert after['travel_reminders']['deliveries'][0]['late']
assert before['itinerary']==after['itinerary'] and before['packing_checklist']==after['packing_checklist'] and before['trip_documents']==after['trip_documents']
print(json.dumps(dict(deliveries=1,late=True,packing=True,documents=data['documents'],finance=result['current']['amounts'])))
'''
        results=[]
        for _ in range(2):
            process=subprocess.run([sys.executable,'-c',program],env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(process.returncode,0,process.stderr[-1000:]);results.append(json.loads(process.stdout))
        self.assertEqual(results[0],results[1])
