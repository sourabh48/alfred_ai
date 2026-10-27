"""One saved trip across PDF/GPX/ICS, edit lifecycles and private-data boundaries."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.db import connection
from django.test import Client, TestCase, override_settings
from lxml import etree
from pypdf import PdfReader

from alfred_private_storage import private_directory
from apps.mobility.models import TravelPlan, TravelPlanningSession
from apps.mobility.services.travel.editor import editor_payload
from apps.mobility.services.travel_conversation import save_plan
from apps.mobility.services.travel_discovery import fact
from tests import test_travel_pdf_export as fixtures
from tests.test_travel_ics_export import parse_calendar


class TravelExportIntegrationTests(TestCase):
    ready=fixtures.TravelPDFExportTests.ready
    researched=fixtures.TravelPDFExportTests.researched
    set_stops=fixtures.TravelPDFExportTests.set_stops
    multi=fixtures.TravelPDFExportTests.multi

    def setUp(self):
        fixtures.TravelPDFExportTests.setUp(self)
        self.session.itinerary,_=editor_payload(self.session)
        start=date(2025,11,2)
        for i,day in enumerate(self.session.itinerary['days']):day['date']=(start+timedelta(days=i)).isoformat()
        self.session.state['available_start_date']=fact(start.isoformat())
        self.session.state['available_end_date']=fact(self.session.itinerary['days'][-1]['date'])
        self.session.itinerary['stops'][0]['sources'].append(dict(source_name='B4 synthetic expired weather',data_type='weather',
            freshness='LIVE',confidence='VERIFIED',retrieved_at='1999-12-31T00:00:00+00:00',valid_until='2000-01-01T00:00:00+00:00'))
        self.session.itinerary['owner_note']='NOT_FOR_EXPORT_UNRELATED'
        self.session.save()
        source=dict(id='a'*32,kind='upload',document_name='NOT_FOR_EXPORT_PRIVATE_DOCUMENT.txt',source_fingerprint='1'*64,expires_at='2050-01-01T00:00:00+00:00')
        self.enterContext(patch('apps.mobility.services.travel.documents.MemoryStore'))
        self.enterContext(patch('apps.mobility.services.travel.documents.DocumentCorpus.list',return_value={'documents':[source]}))
        response=self.post('trip_documents',operation='link',document_id=source['id'],fingerprint=source['source_fingerprint'])
        self.assertEqual(response.status_code,200,response.content[:400])
        packing=self.client.get(self.url).json()['packing_checklist']
        self.assertEqual(self.post('packing',operation='update',checklist_revision=packing['revision'],item_id=packing['items'][0]['id'],label='NOT_FOR_EXPORT_PACKING',packed=True).status_code,200)
        self.assertEqual(self.post('reminders',operation='consent',request_id=str(uuid4()),reminder_revision=0,enabled=True).status_code,200)
        self.assertEqual(self.post('reminders',operation='create',request_id=str(uuid4()),reminder_revision=1,
            reminder_id=str(uuid4()),label='NOT_FOR_EXPORT_REMINDER',zone='UTC',local_time='2050-01-02T10:00').status_code,200)
        self.session.refresh_from_db();save_plan(self.session,draft=True);self.session.refresh_from_db()

    def plan(self):
        return TravelPlan.objects.get(pk=self.session.plan_id)

    def post(self, action, **fields):
        self.session.refresh_from_db()
        if action=='export_ics' and 'calendar' not in fields:
            preview=self.post('calendar_preview')
            fields['calendar']=dict(snapshot=preview.json().get('snapshot','unavailable'),events=[])
        payload=dict(action=action)|({} if action in ('packing','reminders') else dict(revision=self.session.revision))|fields
        return self.client.post(self.url,payload,content_type='application/json')

    def exports(self, calendar=None):
        responses={kind:self.post('export_'+kind,**({'calendar':calendar} if calendar is not None and kind=='ics' else {})) for kind in ('pdf','gpx','ics')}
        for kind,response in responses.items():
            self.assertEqual(response.status_code,200,(kind,response.content[:400]))
            self.assertEqual(response['Cache-Control'],'no-store, private')
            self.assertEqual(response['X-Content-Type-Options'],'nosniff')
            self.assertEqual(response['Referrer-Policy'],'no-referrer')
            self.assertEqual(response['Content-Disposition'],f'attachment; filename="alfred-itinerary.{kind}"')
        return responses

    def parsed(self,responses):
        pdf=PdfReader(BytesIO(responses['pdf'].content),strict=True)
        xml=etree.fromstring(responses['gpx'].content,etree.XMLParser(resolve_entities=False,no_network=True))
        calendar=parse_calendar(responses['ics'].content)
        return '\n'.join(p.extract_text() for p in pdf.pages),xml,calendar

    def private_state(self):
        plan=self.plan()
        return deepcopy((plan.planning_state,plan.itinerary))

    def test_same_trip_truthful_sources_dates_order_dst_and_no_write_or_private_copy(self):
        plan=self.plan();before=self.private_state()
        preview=self.post('calendar_preview').json();first=preview['activities'][0]
        options=dict(snapshot=preview['snapshot'],zone='America/New_York',events=[dict(id=first['id'],confirmed=True,
            start='2025-11-02T01:15',end='2025-11-02T01:45',start_fold=0,end_fold=1)])
        media=private_directory(Path(self.enterContext(TemporaryDirectory()))/'media')
        self.enterContext(override_settings(MEDIA_ROOT=str(media)))
        statements=[]
        def read_only(execute,sql,params,many,context):
            statement=sql.lstrip().split(None,1)[0].upper();statements.append(statement)
            if statement in ('INSERT','UPDATE','DELETE','REPLACE'):
                self.assertTrue(sql.lstrip().upper().startswith('UPDATE "DJANGO_SESSION" SET '),'Only existing authentication-session bookkeeping may write during export')
            return execute(sql,params,many,context)
        with ExitStack() as stack:
            stack.enter_context(connection.execute_wrapper(read_only))
            stack.enter_context(patch('apps.mobility.services.travel.documents.MemoryStore',side_effect=AssertionError('No private corpus access during export')))
            stack.enter_context(patch('alfred_ai.services.public_http.request',side_effect=AssertionError('No external request during export')))
            stack.enter_context(patch('requests.sessions.Session.request',side_effect=AssertionError('No external HTTP during export')))
            stack.enter_context(patch.object(Path,'write_bytes',side_effect=AssertionError('No permanent export copy')))
            responses=self.exports(options)
        pdf,xml,calendar=self.parsed(responses)
        names=[s['name'] for s in plan.itinerary['stops']]
        self.assertEqual(xml.xpath('//*[local-name()="wpt"]/*[local-name()="name"]/text()'),names)
        self.assertFalse(xml.xpath('//*[local-name()="rte" or local-name()="trk" or local-name()="time"]'))
        self.assertLess(pdf.index(names[0]+' → '+names[1]),len(pdf))
        self.assertTrue(all(name in calendar['events'][0]['location'] for name in names))
        for day in plan.itinerary['days']:self.assertIn(day['date'],pdf)
        self.assertEqual(calendar['events'][0]['start'],'2025-11-02T05:15:00Z')
        self.assertEqual(calendar['events'][0]['end'],'2025-11-02T06:45:00Z')
        self.assertEqual([e['summary'] for e in calendar['events']],[item['title'] for day in plan.itinerary['days'] for item in day['items']])
        for text in (pdf,responses['ics'].content.replace(b'\r\n ',b'').decode()):
            for evidence in ('B4 synthetic expired weather','1999-12-31','2000-01-01','CACHED','UNKNOWN'):self.assertIn(evidence,text)
        for response in responses.values():self.assertNotIn(b'NOT_FOR_EXPORT',response.content)
        self.assertEqual(list(media.iterdir()),[]);self.assertTrue(statements)
        self.assertEqual(self.private_state(),before)
        output=private_directory(Path(__file__).resolve().parents[1]/'artifacts/travel-exports-b4-20261028/samples')
        for kind,response in responses.items():(output/f'same-trip.{kind}').write_bytes(response.content)

    def test_save_reopen_edit_stop_order_undo_and_stale_export_versions(self):
        original=self.plan();initial=self.parsed(self.exports())[2]
        private=deepcopy({k:original.planning_state[k] for k in ('_packing_checklist','_travel_reminders','_itinerary_documents')})
        reopened=self.client.post('/api/mobility/planner/sessions/',dict(plan_id=original.pk),content_type='application/json')
        self.assertIn(reopened.status_code,(200,201),reopened.content[:400])
        self.session=TravelPlanningSession.objects.get(pk=reopened.json()['id']);self.url=f'/api/mobility/planner/sessions/{self.session.pk}/'
        self.assertEqual([e['uid'] for e in self.parsed(self.exports())[2]['events']],[e['uid'] for e in initial['events']])
        old_revision=self.session.revision;old_options=self.post('calendar_preview').json()
        day=self.client.get(self.url).json()['itinerary']['days'][0]
        item=next(i for i in day['items'] if i.get('type') not in ('travel','break'));position=day['items'].index(item)
        result=self.post('itinerary_edit',operation='update',request_id=str(uuid4()),day_id=day['id'],item_id=item['id'],fields={'title':'B4 owner edited activity'})
        self.assertEqual(result.status_code,200,result.content[:500])
        for kind in ('pdf','gpx','ics'):
            self.assertEqual(self.post('export_'+kind,revision=old_revision).status_code,409)
        self.assertNotIn('B4 owner edited activity',self.parsed(self.exports())[0])
        save_plan(self.session,draft=True);self.session.refresh_from_db()
        self.assertEqual(self.post('export_ics',calendar=dict(snapshot=old_options['snapshot'],events=[])).status_code,409)
        edited=self.parsed(self.exports());self.assertIn('B4 owner edited activity',edited[0]);self.assertEqual(edited[2]['events'][position]['uid'],initial['events'][position]['uid'])
        self.assertEqual(self.post('itinerary_edit',operation='undo',request_id=str(uuid4())).status_code,200)
        save_plan(self.session,draft=True);self.session.refresh_from_db()
        self.assertEqual(self.parsed(self.exports())[2]['events'][position]['summary'],initial['events'][position]['summary'])
        order=self.client.get(self.url).json()['itinerary_editor']['stops']
        self.assertEqual(self.post('itinerary_edit',operation='order_stops',request_id=str(uuid4()),stops=[s['id'] for s in reversed(order)]).status_code,200)
        save_plan(self.session,draft=True);self.session.refresh_from_db()
        pdf,xml,cal=self.parsed(self.exports());names=[s['name'] for s in reversed(order)]
        self.assertEqual(xml.xpath('//*[local-name()="wpt"]/*[local-name()="name"]/text()'),names)
        self.assertIn(' → '.join(names),pdf);self.assertEqual(cal['events'][0]['location'],' → '.join(names))
        self.assertEqual({k:self.plan().planning_state[k] for k in private},private)

    def test_shared_owner_csrf_auth_revision_boundary_and_failed_render_retry(self):
        before=self.private_state()
        with patch('fitz.Story',side_effect=RuntimeError('NOT_FOR_EXPORT_RENDER_PATH')):
            response=self.post('export_pdf');self.assertEqual(response.status_code,503)
            self.assertNotIn(b'NOT_FOR_EXPORT',response.content)
        self.parsed(self.exports());self.assertEqual(self.private_state(),before)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.user)
        for action in ('calendar_preview','export_pdf','export_gpx','export_ics'):
            response=csrf.post(self.url,dict(action=action,revision=self.session.revision,calendar={}) if action=='export_ics' else dict(action=action,revision=self.session.revision),content_type='application/json')
            self.assertEqual(response.status_code,403)
        self.client.force_login(self.other)
        for kind in ('pdf','gpx','ics'):self.assertEqual(self.post('export_'+kind).status_code,404)
        self.client.logout()
        for kind in ('pdf','gpx','ics'):self.assertIn(self.post('export_'+kind).status_code,(401,403))

    def test_unprepared_builder_export_then_first_edit_keeps_every_calendar_uid(self):
        for day in self.session.itinerary['days']:
            day.pop('id',None)
            for item in day['items']:item.pop('id',None)
        self.session.save(update_fields=['itinerary']);save_plan(self.session,draft=True);self.session.refresh_from_db()
        original=deepcopy(self.plan().itinerary)
        first=self.parsed(self.exports())[2]['events']
        self.assertEqual(self.plan().itinerary,original,'Export must not persist prepared IDs')
        day=self.client.get(self.url).json()['itinerary']['days'][0]
        item=next(i for i in day['items'] if i.get('type') not in ('travel','break'))
        response=self.post('itinerary_edit',operation='update',request_id=str(uuid4()),day_id=day['id'],item_id=item['id'],fields={'title':'B4 first owner edit'})
        self.assertEqual(response.status_code,200,response.content[:400])
        save_plan(self.session,draft=True);self.session.refresh_from_db()
        second=self.parsed(self.exports())[2]['events']
        self.assertEqual([e['uid'] for e in first],[e['uid'] for e in second])

    def test_missing_facts_and_untrusted_titles_keep_format_specific_limits_truthful(self):
        plan=self.plan();title='B4 café <img> ,;\\\r\nATTENDEE:fixture@example.invalid'
        plan.itinerary['days'][0]['items'][0]['title']=title
        plan.itinerary['days'][0]['date']=None
        plan.save(update_fields=['itinerary'])
        responses=self.exports();pdf,xml,cal=self.parsed(responses)
        self.assertIn('B4 café <img>',pdf)
        self.assertTrue(all(event['summary']!=title for event in cal['events']))
        self.assertEqual(responses['ics']['X-ALFRED-Calendar-Warnings'],'1')
        self.assertFalse(xml.xpath('//*[local-name()="trk" or local-name()="rte"]'))
        plan.itinerary['days'][0]['date']=plan.start_date.isoformat();plan.save(update_fields=['itinerary'])
        responses=self.exports();cal=self.parsed(responses)[2]
        self.assertEqual(cal['events'][0]['summary'],title.replace('\r\n','\n'))
        self.assertFalse(any('attendee' in e['properties'] for e in cal['events']))
        plan.planning_state.pop('_itinerary_stops');plan.save(update_fields=['planning_state'])
        self.assertEqual(self.post('export_gpx').status_code,400)
        self.assertEqual(self.post('export_pdf').status_code,200)
        self.assertEqual(self.post('export_ics').status_code,200)
