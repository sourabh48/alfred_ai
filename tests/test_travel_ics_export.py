"""Private calendar contracts checked by a pinned independent RFC5545 parser."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import re
import subprocess

from django.test import Client, TestCase

from alfred_private_storage import private_directory
from apps.mobility.models import TravelPlan
from apps.mobility.services.travel_discovery import fact
from tests import test_travel_pdf_export as fixtures


def parse_calendar(content):
    result=subprocess.run(['node',str(Path(__file__).with_name('ics_parser.cjs'))],input=content,
        capture_output=True,timeout=30)
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors='replace')[-1500:])
    return json.loads(result.stdout)


class TravelICSExportTests(TestCase):
    ready=fixtures.TravelPDFExportTests.ready
    researched=fixtures.TravelPDFExportTests.researched
    set_stops=fixtures.TravelPDFExportTests.set_stops
    multi=fixtures.TravelPDFExportTests.multi
    setUp=fixtures.TravelPDFExportTests.setUp

    def plan(self):
        return TravelPlan.objects.get(pk=self.session.plan_id)

    def preview(self):
        self.session.refresh_from_db()
        response=self.client.post(self.url,dict(action='calendar_preview',revision=self.session.revision),content_type='application/json')
        self.assertEqual(response.status_code,200,response.content[:500])
        return response.json()

    def export(self, options=None, **fields):
        self.session.refresh_from_db()
        if options is None:
            preview=self.client.post(self.url,dict(action='calendar_preview',revision=self.session.revision),content_type='application/json')
            options=dict(snapshot=preview.json().get('snapshot','unavailable'),events=[])
        return self.client.post(self.url,dict(action='export_ics',revision=self.session.revision,calendar=options)|fields,content_type='application/json')

    def parsed(self,response):
        self.assertEqual(response.status_code,200,response.content[:500])
        self.assertEqual(response['Content-Type'],'text/calendar; charset=utf-8')
        self.assertTrue(response.content.endswith(b'END:VCALENDAR\r\n'))
        self.assertTrue(all(len(line)<=75 for line in response.content.split(b'\r\n')))
        parsed=parse_calendar(response.content)
        self.assertTrue(parsed['roundtrip'])
        return parsed

    def window(self, start):
        plan=self.plan();start=date.fromisoformat(start)
        plan.start_date=start;plan.end_date=start+timedelta(days=len(plan.itinerary['days'])-1)
        plan.planning_state['available_start_date']=fact(start.isoformat())
        plan.planning_state['available_end_date']=fact(plan.end_date.isoformat())
        for i,day in enumerate(plan.itinerary['days']):day['date']=(start+timedelta(days=i)).isoformat()
        plan.save(update_fields=['start_date','end_date','planning_state','itinerary'])

    def timed(self, start, end, **extra):
        choices=self.preview();key=choices['activities'][0]['id']
        return dict(snapshot=choices['snapshot'],zone='Asia/Kolkata',events=[dict(id=key,confirmed=True,start=start,end=end)|extra])

    def test_date_only_exclusive_end_private_headers_stable_identifiers_and_roundtrip(self):
        choices=self.preview();self.assertTrue(choices['activities'])
        response=self.export();parsed=self.parsed(response)
        events=parsed['events'];self.assertTrue(all(e['date'] for e in events))
        self.assertEqual(events[0]['start'],self.plan().start_date.isoformat())
        self.assertEqual(events[0]['end'],(self.plan().start_date+timedelta(days=1)).isoformat())
        self.assertEqual([e['uid'] for e in events],[e['uid'] for e in self.parsed(self.export())['events']])
        self.assertTrue(all(re.fullmatch('[0-9a-f]{64}@alfred.local',e['uid']) for e in events))
        self.assertNotIn('method',parsed['properties'])
        for event in events:
            self.assertFalse(event['components'])
            self.assertFalse({'attendee','organizer','attach','alarm','url'}&set(event['properties']))
        for key,val in [('Cache-Control','no-store, private'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),('Content-Disposition','attachment; filename="alfred-itinerary.ics"')]:self.assertEqual(response[key],val)
        self.assertEqual(response['X-ALFRED-Calendar-Warnings'],'0')
        out=private_directory(Path(__file__).resolve().parents[1]/'artifacts/travel-ics-20261027')
        (out/'synthetic-calendar.ics').write_bytes(response.content)

    def test_confirmed_timed_overnight_and_multi_day_ranges_preserve_local_context(self):
        self.window('2035-01-02')
        options=self.timed('2035-01-02T22:30','2035-01-03T06:15')
        event=self.parsed(self.export(options))['events'][0]
        self.assertEqual(event['start'],'2035-01-02T17:00:00Z');self.assertEqual(event['end'],'2035-01-03T00:45:00Z')
        self.assertFalse(event['date']);self.assertIn('Asia/Kolkata',event['description'])
        self.assertNotIn(b'TZID',self.export(options).content)
        options['events'][0]['end']='2035-01-05T06:15'
        self.assertEqual(self.parsed(self.export(options))['events'][0]['end'],'2035-01-05T00:45:00Z')
        choices=self.preview();row=choices['activities'][0]
        ranged=self.parsed(self.export(dict(snapshot=choices['snapshot'],events=[dict(id=row['id'],confirmed=True,through='2035-01-04')])) )['events'][0]
        self.assertEqual(ranged['end'],'2035-01-05');self.assertTrue(ranged['date'])
        self.assertEqual(ranged['uid'],event['uid'])

    def test_dst_gap_is_rejected_and_fold_requires_explicit_occurrence_evidence(self):
        self.window('2025-03-09');options=self.timed('2025-03-09T02:30','2025-03-09T04:00');options['zone']='America/New_York'
        response=self.export(options);self.assertEqual(response.status_code,400);self.assertIn('does not exist',response.content.decode())
        self.window('2025-11-02');options=self.timed('2025-11-02T01:15','2025-11-02T01:45');options['zone']='America/New_York'
        response=self.export(options);self.assertEqual(response.status_code,400);self.assertIn('occurs twice',response.content.decode())
        options['events'][0].update(start_fold=0,end_fold=1)
        event=self.parsed(self.export(options))['events'][0]
        self.assertEqual((event['start'],event['end']),('2025-11-02T05:15:00Z','2025-11-02T06:45:00Z'))

    def test_missing_unconfirmed_and_unsupported_dates_are_omitted_with_explicit_warnings(self):
        plan=self.plan()
        for invalid in (None,'2035-02-30','unsupported'):
            plan.itinerary['days'][0]['date']=invalid;plan.save(update_fields=['itinerary'])
            preview=self.preview();self.assertTrue(preview['warnings'])
            response=self.export();self.parsed(response);self.assertEqual(response['X-ALFRED-Calendar-Warnings'],'1')
            self.assertIn(b'activities omitted',response.content.replace(b'\r\n ',b''))
        plan.planning_state['available_start_date']['confirmed_by_user']=False;plan.save(update_fields=['planning_state'])
        self.assertEqual(self.preview()['activities'],[])
        self.assertEqual(self.export().status_code,400)

    def test_date_only_does_not_infer_times_from_period_or_duration_or_timezone(self):
        plan=self.plan();plan.itinerary['days'][0]['items'][0].update(period='Depart 08:00',duration='Estimated2hours')
        plan.save(update_fields=['itinerary'])
        options=dict(snapshot=self.preview()['snapshot'],zone='Pacific/Auckland',events=[])
        event=self.parsed(self.export(options))['events'][0]
        self.assertTrue(event['date']);self.assertEqual(event['start'],plan.start_date.isoformat())
        self.assertIn('unverified',event['description'])

    def test_unicode_escaping_folding_and_crlf_injection_do_not_add_properties_or_events(self):
        plan=self.plan();title='Café यात्रा,;\\\r\nATTENDEE:test@example.invalid '
        plan.itinerary['days'][0]['items'][0]['title']=title+'X'*160
        plan.save(update_fields=['itinerary'])
        response=self.export();events=self.parsed(response)['events']
        self.assertEqual(events[0]['summary'],(title+'X'*160).replace('\r\n','\n'))
        self.assertEqual(len(events),len(self.preview()['activities']))
        self.assertFalse(any('attendee' in event['properties'] for event in events))
        self.assertNotIn(b'\nATTENDEE:',response.content)

    def test_saved_only_excludes_private_state_and_does_not_mutate_the_trip(self):
        plan=self.plan();plan.itinerary['owner_note']='NOT_FOR_ICS_PRIVATE_NOTE'
        plan.planning_state['private_record']=fact('NOT_FOR_ICS_ACCOUNT_DATA')
        plan.itinerary['budget']['expected']='987654321.99';plan.save(update_fields=['planning_state','itinerary'])
        before=deepcopy((plan.planning_state,plan.itinerary))
        self.session.itinerary={};self.session.state={};self.session.save(update_fields=['state','itinerary'])
        response=self.export();self.parsed(response)
        self.assertNotIn(b'NOT_FOR_ICS',response.content);self.assertNotIn(b'987654321.99',response.content)
        plan.refresh_from_db();self.assertEqual((plan.planning_state,plan.itinerary),before)

    def test_auth_owner_csrf_session_revision_and_saved_snapshot_conflicts(self):
        choices=self.preview();self.assertEqual(self.export(revision=self.session.revision+1).status_code,409)
        self.assertEqual(self.export(extra=True).status_code,400)
        plan=self.plan();plan.title+=' changed';plan.save(update_fields=['title'])
        self.assertEqual(self.export(dict(snapshot=choices['snapshot'])).status_code,409)
        choices=self.preview();plan.itinerary['destination']='Changed saved location';plan.save(update_fields=['itinerary'])
        self.assertEqual(self.export(dict(snapshot=choices['snapshot'])).status_code,409)
        self.client.force_login(self.other);self.assertEqual(self.export().status_code,404)
        self.client.logout();self.assertIn(self.export().status_code,(401,403))
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post(self.url,dict(action='calendar_preview',revision=0),content_type='application/json').status_code,403)

    def test_malformed_duplicate_oversized_and_unconfirmed_options_fail_without_partial_ics(self):
        self.window('2035-01-02');original=self.timed('2035-01-02T10:00','2035-01-02T11:00')
        cases=[dict(original,events=original['events']*2),dict(original,zone='Invalid/Timezone'),dict(original,events=original['events']*21),dict(original,attendee='hidden')]
        for fields in [dict(confirmed=False),dict(id='unknown'),dict(end=''),dict(start='2035-01-03T10:00'),dict(end='2035-01-02T09:00'),dict(start_fold=True)]:
            cases.append(dict(original,events=[original['events'][0]|fields]))
        for options in cases:
            response=self.export(options);self.assertEqual(response.status_code,400,response.content[:500]);self.assertFalse(response.content.startswith(b'BEGIN:VCALENDAR'))
        plan=self.plan();plan.itinerary['days'][0]['items']=[{}]*31;plan.save(update_fields=['itinerary'])
        self.assertEqual(self.export().status_code,400)

    def test_persisted_item_identity_survives_title_changes_and_final_date_is_explicitly_omitted(self):
        plan=self.plan();plan.itinerary['days'][0]['items'][0]['id']='saved-item-001'
        plan.save(update_fields=['itinerary']);first=self.parsed(self.export())['events'][0]
        plan.itinerary['days'][0]['items'][0]['title']='Owner corrected activity name';plan.save(update_fields=['itinerary'])
        second=self.parsed(self.export())['events'][0]
        self.assertEqual(first['uid'],second['uid']);self.assertNotEqual(first['summary'],second['summary'])
        plan.start_date=plan.end_date=date.max
        plan.planning_state['available_start_date']=fact(date.max.isoformat());plan.planning_state['available_end_date']=fact(date.max.isoformat())
        plan.itinerary['days']=[dict(date=date.max.isoformat(),items=[dict(title='Unsupported exclusive end')])]
        plan.save(update_fields=['start_date','end_date','planning_state','itinerary'])
        self.assertTrue(self.preview()['warnings']);self.assertEqual(self.export().status_code,400)
