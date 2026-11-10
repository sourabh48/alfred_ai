"""Real synthetic Career rows, no model or provider required for recorded progress."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase

from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume
from apps.career.services.application_tracker import apply_change
from apps.ml_engine.services.assistant_tools import execute_tool, ToolInputError
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer, _read_source_context
from apps.ml_engine.services.persistent_memory import MemoryConflict


class CareerAssistantTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='synthetic-career-tool')
        self.other = get_user_model().objects.create_user(username='synthetic-career-tool-other')
        self.client.force_login(self.owner)
        self.today = self.enterContext(patch('apps.ml_engine.services.career_evidence.timezone.localdate',
                                           return_value=date(2026, 11, 11)))
        self.row = self.record(self.owner)
        self.record(self.other, company='OTHER-OWNER-SECRET')

    def record(self, owner, **fields):
        return CareerJobAnalysis.objects.create(user=owner, job_url='https://example.invalid/private',
            extracted_text='PRIVATE-RAW-JD', summary='PRIVATE-SUMMARY',
            extracted_payload={'salary': 'PRIVATE-SALARY', 'application': apply_change({},
                {'stage': 'applied', 'on': '2026-11-01'}, today=date(2026, 11, 11))}, **fields)

    def read(self, owner=None):
        return execute_tool(owner or self.owner, 'career.applications', {}, consent=True)

    def post(self, **extra):
        return self.client.post('/api/ai/personal-insights/',
            dict(query='Summarize my application progress', scope='career', **extra), content_type='application/json')

    def test_real_owned_counts_follow_up_timing_and_privacy_without_writes_or_network(self):
        before = list(CareerJobAnalysis.objects.values())
        writes = []
        def observe(execute, sql, params, many, context):
            if sql.lstrip().split()[0].upper() in ('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'REPLACE', 'DROP'):
                writes.append(sql)
            return execute(sql, params, many, context)
        with connection.execute_wrapper(observe), patch('socket.socket.connect', side_effect=AssertionError('No network')):
            result = self.read()
        data = result[0]['data']
        self.assertEqual(data['total_saved_opportunities'], 1)
        self.assertEqual(data['opportunities_scanned'], 1)
        self.assertIn('applied: 1', data['progress'])
        self.assertIn('Next follow-up due 2026-11-08', data['recent_opportunities'][0])
        self.assertIn('not independent', data['limitations'][0])
        for secret in ('PRIVATE-', 'OTHER-OWNER', 'https://'):
            self.assertNotIn(secret, str(result))
        self.assertEqual(list(CareerJobAnalysis.objects.values()), before)
        self.assertFalse(CareerProfile.objects.exists())
        self.assertFalse(CareerResume.objects.exists())
        self.assertEqual(writes, [])

    def test_missing_malformed_and_future_dates_never_invent_a_follow_up(self):
        invalid = ({}, {'history': None}, {'history': 'bad'}, {'history': [{'stage': 'applied'}]},
            {'history': [{'stage': 'applied', 'on': '2026-02-30'}]},
            {'history': [{'stage': 'applied', 'on': '2026-12-01'}]},
            {'history': [{'stage': 'applied', 'on': '2026-11-01'}], 'follow_ups': [1]},
            {'history': [{'stage': 'applied', 'on': '2026-11-01'}]*61})
        for fields in invalid:
            with self.subTest(fields=fields):
                self.row.extracted_payload = {'application': dict(stage='applied', **fields)}
                self.row.save()
                self.assertIn('Unavailable: review', self.read()[0]['data']['recent_opportunities'][0])

    def test_invalid_stages_and_json_are_unresolved_instead_of_confirmed(self):
        for application in (None, [], True, 'applied', {}, {'stage': []}, {'stage': 'SYNTHETIC-INJECTION'}):
            with self.subTest(application=application):
                CareerJobAnalysis.objects.filter(pk=self.row.pk).update(extracted_payload={'application': application})
                data = self.read()[0]['data']
                self.assertEqual(data['no_valid_stage_recorded'], 1)
                self.assertIn('No valid stage recorded', data['recent_opportunities'][0])
                self.assertNotIn('SYNTHETIC-INJECTION', str(data))

    def test_bounded_scan_and_empty_owner_distinguish_omitted_from_no_records(self):
        empty = get_user_model().objects.create_user(username='synthetic-career-empty')
        data = self.read(empty)[0]['data']
        self.assertEqual(data['total_saved_opportunities'], 0)
        self.assertEqual(data['recent_opportunities'], [])
        CareerJobAnalysis.objects.bulk_create([CareerJobAnalysis(user=self.owner) for _ in range(301)])
        data = self.read()[0]['data']
        self.assertEqual((data['total_saved_opportunities'], data['opportunities_scanned'], data['opportunities_outside_scan']), (302, 300, 2))
        self.assertEqual(len(data['recent_opportunities']), 3)
        self.assertEqual(data['no_valid_stage_recorded'], 300)

    def test_revision_binds_owner_deletion_new_records_and_stage_updates(self):
        original = self.read()[0]['revision']
        CareerJobAnalysis.objects.filter(pk=self.row.pk).update(extracted_payload={'application': {'stage': 'interview'}})
        changed = self.read()[0]['revision']
        self.assertNotEqual(changed, original)
        self.row.delete()
        self.assertNotEqual(self.read()[0]['revision'], changed)
        self.assertNotEqual(self.read()[0]['revision'], self.read(self.other)[0]['revision'])
        self.assertEqual(self.read()[0]['data']['total_saved_opportunities'], 0)

    def test_revalidation_rejects_changed_evidence_before_returning_an_answer(self):
        def changed(user, scope, **kwargs):
            result = _read_source_context(user, scope, **kwargs)
            CareerJobAnalysis.objects.filter(pk=self.row.pk).update(extracted_payload={'application': {'stage': 'interview'}})
            return result
        with patch('apps.ml_engine.services.hybrid_intelligence._read_source_context', side_effect=changed), self.assertRaises(MemoryConflict):
            hybrid_answer(None, self.owner, 'Application progress?', scope='career')

    def test_api_is_page_only_session_bound_and_works_without_a_memory_vault_or_model(self):
        with (patch('apps.ml_engine.api.views.memory_store', side_effect=AssertionError('No vault')),
                patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner', side_effect=AssertionError('No model')),
                patch('socket.socket.connect', side_effect=AssertionError('No network'))):
            response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['grounding'], 'recorded_career_progress')
        self.assertEqual(response.json()['provider'], 'local_evidence')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.post(cloud_consent=True).status_code, 403)
        self.assertEqual(self.post(conversation_id='a'*32).status_code, 400)
        self.assertEqual(self.post(page_context=[]).status_code, 400)
        self.client.logout()
        self.assertEqual(self.post().status_code, 403)

    def test_no_foreign_inputs_or_side_effects_and_csrf_still_required(self):
        for arguments in ({'owner_id': self.other.pk}, {'document_id': 1}):
            with self.assertRaises(ToolInputError):
                execute_tool(self.owner, 'career.applications', arguments, consent=True)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post('/api/ai/personal-insights/',
            {'scope': 'career', 'query': 'Application progress'}, content_type='application/json').status_code, 403)

    def test_active_owner_is_rechecked_and_logout_during_read_discards_response(self):
        from apps.ml_engine.api.conversations import current_session
        from django.contrib.sessions.models import Session
        checks = []
        def check(request):
            checks.append(True)
            if len(checks) == 2:
                Session.objects.filter(session_key=request.session.session_key).delete()
            return current_session(request)
        with patch('apps.ml_engine.api.conversations.current_session', side_effect=check):
            self.assertEqual(self.post().status_code, 403)
        self.assertEqual(len(checks), 2)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionError):
            self.read()
