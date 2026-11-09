"""Synthetic diagnostics and native heartbeat regressions."""
import io
import json
import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase

from alfred_ai.services.local_diagnostics import _chat_probe, benchmark_local_ai
from alfred_ai.services.native_readiness import native_heartbeat_ready
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable


class HeartbeatTests(SimpleTestCase):
    def test_only_current_instance_finite_recent_heartbeats_are_ready(self):
        with patch.dict('os.environ', {'ALFRED_NATIVE_INSTANCE': 'synthetic-instance'}), patch('time.time', return_value=100):
            self.assertTrue(native_heartbeat_ready({'instance': 'synthetic-instance', 'time': 99}, 15))
            for heartbeat in (None, [], {}, {'instance': 'foreign', 'time': 99}, *(
                    {'instance': 'synthetic-instance', 'time': value}
                    for value in (None, '99', True, float('nan'), float('inf'), 101, 85))):
                with self.subTest(heartbeat=heartbeat):
                    self.assertFalse(native_heartbeat_ready(heartbeat, 15))
        with patch.dict('os.environ', {}, clear=True):
            self.assertFalse(native_heartbeat_ready({'time': time.time()}, 15))

    def test_native_health_rejects_unbound_or_malformed_heartbeat(self):
        from alfred_ai.native_views import native_health
        with patch('alfred_ai.native_views.connection') as database, patch('alfred_ai.native_views.cache') as cached:
            for heartbeat in (None, {}, {'time': time.time()}):
                cached.get.return_value = heartbeat
                with patch.dict('os.environ', {}, clear=True):
                    self.assertEqual(native_health(None).status_code, 503)


class InferenceProbeTests(SimpleTestCase):
    def probe(self, parts, fragment=False):
        reasoner = Mock(model='synthetic-local')
        reasoner._digest.return_value = 'a' * 64
        response = Mock(status=200)
        response.getheader.return_value = 'identity'
        stream = io.BytesIO(b''.join(json.dumps(p).encode() + b'\n' for p in parts))
        response.read1.side_effect = (lambda _: stream.read1(7)) if fragment else stream.read1
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('alfred_ai.services.local_diagnostics.HTTPConnection', return_value=connection) as factory:
            result = _chat_probe(reasoner, time.monotonic() + 5)
        factory.assert_called_once()
        self.assertEqual(factory.call_args.args[:2], ('127.0.0.1', 11434))
        connection.close.assert_called_once()
        payload = json.loads(connection.request.call_args.args[2])
        self.assertEqual(payload['messages'], [{'role': 'user', 'content': 'Reply with the words ALFRED local inference is working.'}])
        self.assertTrue(payload['stream'])
        return result

    def test_real_content_and_completed_stream_required_and_metrics_are_bounded(self):
        result = self.probe([
            {'model': 'synthetic-local', 'message': {'role': 'assistant', 'content': 'ALFRED'}},
            {'model': 'synthetic-local', 'message': {'role': 'assistant', 'content': ''}, 'done': True,
             'load_duration': 1_000_000, 'eval_duration': 1_000_000_000, 'eval_count': 10}], fragment=True)
        self.assertEqual(result['output_tokens_per_second'], 10)
        self.assertEqual(result['load_seconds'], .001)
        self.assertGreaterEqual(result['first_token_seconds'], 0)
        self.assertNotIn('ALFRED', str(result))

    def test_partial_empty_foreign_and_tool_responses_fail_closed(self):
        for parts in (
            [{'model': 'synthetic-local', 'message': {'role': 'assistant', 'content': 'partial'}}],
            [{'model': 'synthetic-local', 'message': {'role': 'assistant', 'content': ''}, 'done': True}],
            [{'model': 'foreign', 'message': {'role': 'assistant', 'content': 'text'}, 'done': True}],
            [{'model': 'synthetic-local', 'message': {'role': 'assistant', 'content': 'text', 'tool_calls': [{}]}, 'done': True}],
        ):
            with self.subTest(parts=parts), self.assertRaises(EmbeddingUnavailable):
                self.probe(parts)

    def test_outage_is_redacted_and_no_cloud_fallback(self):
        with patch('alfred_ai.services.local_diagnostics.OllamaEmbeddings') as embeddings, \
                patch('alfred_ai.services.local_diagnostics.OllamaReasoner') as chat:
            embeddings.return_value.embed.side_effect = EmbeddingUnavailable('SYNTHETIC-PRIVATE-error')
            embeddings.return_value._request.side_effect = EmbeddingUnavailable()
            chat.side_effect = EmbeddingUnavailable('SYNTHETIC-PRIVATE-error')
            results = benchmark_local_ai()
        self.assertEqual([r['state'] for r in results], ['error', 'error'])
        self.assertNotIn('SYNTHETIC-PRIVATE', str(results))


class DiagnosticsViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='synthetic-diagnostics')
        cache.delete('native:diagnostics:inference')

    def test_signin_required_and_get_never_runs_inference(self):
        with patch('alfred_ai.diagnostics_views.benchmark_local_ai') as probe:
            self.assertEqual(self.client.get('/settings/diagnostics/').status_code, 302)
            self.client.force_login(self.user)
            response = self.client.get('/settings/diagnostics/')
            self.assertContains(response, 'Unverified until tested')
            self.assertContains(response, 'Test local AI now')
            self.assertNotContains(response, str(__file__))
            self.assertEqual(response.context['database_path'], '')
            self.assertIn('no-store', response['Cache-Control'])
            probe.assert_not_called()

    def test_post_requires_csrf_and_is_globally_rate_limited(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        with patch('alfred_ai.diagnostics_views.benchmark_local_ai', return_value=[]) as probe:
            self.assertEqual(client.post('/settings/diagnostics/').status_code, 403)
            client.get('/settings/diagnostics/')
            token = client.cookies['csrftoken'].value
            self.assertEqual(client.post('/settings/diagnostics/', HTTP_X_CSRFTOKEN=token).status_code, 200)
            response = client.post('/settings/diagnostics/', HTTP_X_CSRFTOKEN=token)
            self.assertContains(response, 'Wait one minute and retry')
            probe.assert_called_once_with()
