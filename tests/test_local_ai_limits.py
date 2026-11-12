"""Owner decision 2026-11-12: local AI limits come from config/local.env; the host stays this PC or the private LAN."""
import time
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.ml_engine.services import local_ai_limits as limits
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable


class FakeClient:
    model = 'synthetic-local:4b'

    def __init__(self, info):
        self.info, self.calls = info, []

    def _request(self, method, path, payload=None, *, deadline=None):
        self.calls.append((method, path, payload))
        if isinstance(self.info, Exception):
            raise self.info
        return {'model_info': self.info}


class LocalAiLimitTests(SimpleTestCase):
    def setUp(self):
        limits._windows.clear()
        self.addCleanup(limits._windows.clear)

    def test_host_must_be_this_pc_or_a_private_lan_address(self):
        self.assertEqual(limits.ollama_address(), ('127.0.0.1', 11434))
        for host, port, expected in (('localhost', 11434, ('127.0.0.1', 11434)), ('192.168.1.20', 8080, ('192.168.1.20', 8080)),
                                     ('10.0.0.5', 11434, ('10.0.0.5', 11434)), ('::1', 11434, ('::1', 11434))):
            with self.subTest(host=host), override_settings(ALFRED_OLLAMA_HOST=host, ALFRED_OLLAMA_PORT=port):
                self.assertEqual(limits.ollama_address(), expected)
        for host, port in (('8.8.8.8', 11434), ('ollama.example.com', 11434), ('169.254.169.254', 80), ('0.0.0.0', 11434),
                           ('', 11434), ('127.0.0.1', 0), ('127.0.0.1', 70000)):
            with self.subTest(host=host, port=port), override_settings(ALFRED_OLLAMA_HOST=host, ALFRED_OLLAMA_PORT=port), \
                    self.assertRaises(EmbeddingUnavailable):
                limits.ollama_address()

    @override_settings(ALFRED_LOCAL_AI_TIMEOUT_SECONDS=600, ALFRED_LOCAL_AI_MAX_OUTPUT_TOKENS=8192)
    def test_timeout_and_output_follow_the_owner_settings(self):
        self.assertEqual((limits.timeout_seconds(), limits.max_output_tokens()), (600, 8192))
        self.assertAlmostEqual(limits.deadline() - time.monotonic(), 600, delta=5)

    def test_window_is_the_models_own_capped_by_the_setting_and_read_once_per_digest(self):
        client = FakeClient({'general.architecture': 'qwen3', 'qwen3.context_length': 16384})
        self.assertEqual(limits.context_tokens(client), limits.FALLBACK_CONTEXT_TOKENS)  # unknown until learned
        limits.learn_window(client, 'a' * 64)
        limits.learn_window(client, 'a' * 64)
        self.assertEqual(limits.context_tokens(client), 16384)
        self.assertEqual(client.calls, [('POST', '/api/show', {'model': client.model})])
        client.info = {'qwen3.context_length': 262144}
        limits.learn_window(client, 'b' * 64)  # a new model digest is read again
        self.assertEqual(limits.context_tokens(client), 32768)
        with override_settings(ALFRED_LOCAL_AI_MAX_CONTEXT_TOKENS=131072):
            self.assertEqual(limits.context_tokens(client), 131072)

    def test_an_unreadable_window_uses_the_fallback_and_is_retried(self):
        for info in (EmbeddingUnavailable('down'), {}, {'qwen3.context_length': 'big'}, {'qwen3.context_length': True}):
            with self.subTest(info=info):
                client = FakeClient(info)
                limits.learn_window(client, 'a' * 64)
                limits.learn_window(client, 'a' * 64)
                self.assertEqual(limits.context_tokens(client), limits.FALLBACK_CONTEXT_TOKENS)
                self.assertEqual(len(client.calls), 2)
        self.assertEqual(limits.context_tokens(object()), limits.FALLBACK_CONTEXT_TOKENS)

    def test_context_bytes_leave_room_for_the_prompt_and_answer(self):
        self.assertEqual(limits.context_bytes(8192, 256), (8192 - 256 - 1024) * 3)
        self.assertEqual(limits.context_bytes(2048, 4096), 4096)  # never below the former fixed cap


class ReasonerUsesTheLearnedWindowTests(SimpleTestCase):
    def setUp(self):
        limits._windows.clear()
        self.addCleanup(limits._windows.clear)

    def test_reason_sends_the_real_window_and_the_owners_output_budget(self):
        from apps.ml_engine.services.hybrid_intelligence import OllamaReasoner
        from apps.ml_engine.services.local_embeddings import OllamaEmbeddings
        reasoner = OllamaReasoner()
        bodies = []

        def request(method, path, payload=None, *, deadline=None):
            if path == '/api/show':
                return {'model_info': {'qwen3.context_length': 16384}}
            bodies.append(payload)
            return dict(model=reasoner.model, done=True, message=dict(role='assistant', content='Synthetic answer.'))

        with patch.object(OllamaEmbeddings, '_digest', return_value='a' * 64), patch.object(reasoner, '_request', side_effect=request):
            reasoner.reason({'query': 'Synthetic', 'response_style': 'detailed'}, max_output_tokens=2048, deadline=time.monotonic() + 5)
            self.assertEqual((bodies[0]['options']['num_ctx'], bodies[0]['options']['num_predict']), (16384, 2048))
            big = {'query': 'Synthetic', 'sources': [{'ref': 'synthetic', 'data': 'x' * limits.context_bytes(16384, 256)}]}
            with self.assertRaisesRegex(ValueError, 'Local context exceeds its limit'):
                reasoner.reason(big, deadline=time.monotonic() + 5)
            with self.assertRaises(ValueError):
                reasoner.reason({'query': 'Synthetic'}, max_output_tokens=limits.max_output_tokens() + 1, deadline=time.monotonic() + 5)


class CitedRecordFigureTests(SimpleTestCase):
    def sources(self):
        return [{'ref': 'loan-closure-1', 'data': {'amounts': {'outstanding': {'amount': '1234.50', 'currency': None}},
                                                   'closure_date': '2026-10-01'}},
                {'ref': 'loan-closure-12', 'data': {'amounts': {'outstanding': {'amount': '999.00', 'currency': None}}}}]

    def present(self, answer, provider='ollama'):
        from apps.ml_engine.services.hybrid_intelligence import present_answer
        return present_answer({'answer': answer, 'sources': self.sources(), 'provider': provider}, 'finance')

    def test_a_recorded_amount_beside_its_ref_is_kept(self):
        result = self.present('The outstanding balance was 1,234.50 [loan-closure-1] on 2026-10-01.')
        self.assertFalse(result['narrative_withheld'])
        self.assertTrue(result['cited_record_figures'])
        self.assertIn('1,234.50', result['answer'])

    def test_invented_converted_or_uncited_figures_are_withheld(self):
        for answer in ('The outstanding balance was 1,234.50.',                          # no citation
                       'About 1,235 is outstanding [loan-closure-1].',                    # rounded
                       'The total is 2233.50 [loan-closure-1] [loan-closure-12].',        # calculated
                       'It was ₹1,234.50 [loan-closure-1].',                              # currency not recorded
                       'It was 1,234.50 INR [loan-closure-1].',
                       'It was 999.00 [loan-closure-1].',                                 # another record's figure, wrong citation
                       'It was 1,234.50 [loan-closure-1] by 2026-12-31.'):                # date not in the record
            with self.subTest(answer=answer):
                result = self.present(answer)
                self.assertTrue(result['narrative_withheld'])
                self.assertNotIn('cited_record_figures', result)
        self.assertTrue(self.present('It was 1,234.50 [loan-closure-1].', provider='openai')['narrative_withheld'])
