import io
import json
import time
from unittest.mock import patch
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.ml_engine.core.alfred_router import alfred_router
from apps.ml_engine.services.gemini_development import GeminiDevelopmentReasoner, PAYLOAD, PROMPT, MODEL
from apps.ml_engine.services.memory_sync import SyncUnavailable


@override_settings(DEBUG=True, ALFRED_GEMINI_DEV_ENABLED=True)
class GeminiDevelopmentTests(SimpleTestCase):
    def setUp(self):
        self.enterContext(patch.dict('os.environ', {'GEMINI_API_KEY': 'synthetic-test-key'}))
        self.http = self.enterContext(patch('apps.ml_engine.services.gemini_development.request', return_value=PublicResponse(
            json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'role': 'model', 'parts': [{'text': 'ALFRED_GEMINI_OK'}]}}]}).encode(), 'application/json')))

    def run_smoke(self):
        return alfred_router.route('gemini-development-smoke', {})

    def test_official_transport_is_bounded_and_only_contains_fixed_synthetic_text(self):
        self.assertEqual(self.run_smoke()['status'], 'ok')
        args, kwargs = self.http.call_args
        self.assertEqual(args, ('POST', f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'))
        self.assertNotIn('key=', args[1])
        self.assertEqual(kwargs['json_body']['contents'], [{'role': 'user', 'parts': [{'text': PROMPT}]}])
        self.assertEqual(kwargs['max_bytes'], 16384)
        self.assertLessEqual(kwargs['deadline']-time.monotonic(), 15)
        self.assertEqual(kwargs['headers']['x-goog-api-key'], 'synthetic-test-key')

    def test_opt_in_debug_and_unpackaged_runtime_are_all_required(self):
        for setting in ({'ALFRED_GEMINI_DEV_ENABLED': False}, {'DEBUG': False}):
            with self.settings(**setting):
                self.assertEqual(self.run_smoke()['status'], 'unavailable')
        with patch('sys.frozen', True, create=True):
            self.assertEqual(self.run_smoke()['reason'], 'not_development')
        self.http.assert_not_called()

    def test_missing_key_and_arbitrary_context_never_send_a_request(self):
        for key in ('', 'invalid\nheader'):
            with patch.dict('os.environ', {'GEMINI_API_KEY': key}):
                self.assertEqual(self.run_smoke()['reason'], 'missing_or_invalid_key')
        for payload in ({'query': 'personal material'}, {'memories': []}, None):
            self.assertEqual(alfred_router.route('gemini-development-smoke', payload)['reason'], 'synthetic_only')
        with self.assertRaises(SyncUnavailable):
            GeminiDevelopmentReasoner().reason({'query': PROMPT, 'memories': ['private']}, max_output_tokens=128, deadline=time.monotonic()+10)
        with self.assertRaises(SyncUnavailable):
            GeminiDevelopmentReasoner().reason(PAYLOAD, max_output_tokens=999, deadline=time.monotonic()+10)
        self.http.assert_not_called()

    def test_errors_are_sanitized_and_do_not_retry_or_fall_back(self):
        for code in ('timeout', 'quota_exhausted', 'authorization_failed', 'synthetic-secret-detail'):
            self.http.reset_mock()
            self.http.side_effect = PublicHTTPError(code)
            result = self.run_smoke()
            self.assertEqual(result['status'], 'unavailable')
            self.assertNotIn('synthetic-secret', json.dumps(result))
            self.http.assert_called_once()

    def test_blocked_truncated_malformed_or_nontext_output_fails_closed(self):
        for data in ({}, {'candidates': None}, {'candidates': []}, {'candidates': [None]},
                {'candidates': [{'finishReason': 'MAX_TOKENS'}]},
                {'candidates': [{'finishReason': 'STOP', 'content': {'role': 'model', 'parts': [{'functionCall': {}}]}}]},
                {'candidates': [{'finishReason': 'STOP', 'content': {'role': 'model', 'parts': [{'text': 'wrong'}]}}]}):
            self.http.return_value = PublicResponse(json.dumps(data).encode(), 'application/json')
            self.assertEqual(self.run_smoke()['reason'], 'invalid_response')

    def test_command_prints_only_sanitized_status_and_existing_routes_stay_local(self):
        output = io.StringIO()
        call_command('gemini_smoke', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['status'], 'ok')
        self.assertNotIn('synthetic-test-key', output.getvalue())
        with patch('apps.ml_engine.core.alfred_router._load_adapter', return_value=None):
            self.assertEqual(alfred_router.route('unconfigured-local-task', {}), {'error': 'Invalid task'})
        self.http.assert_called_once()
