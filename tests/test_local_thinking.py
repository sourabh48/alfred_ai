"""Auto thinking: hard general/travel questions may think first, with their own budget; nothing else changes."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.ml_engine.services import local_ai_limits as limits
from apps.ml_engine.services.hybrid_intelligence import OllamaReasoner, hybrid_answer, wants_thinking
from apps.ml_engine.services.local_chat_stream import LocalChatStream, GenerationIncomplete
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore
from tests.test_local_chat_stream import WireResponse
from tests.test_persistent_memory import SyntheticEmbeddings

PUZZLE = 'Solve this logic puzzle: five friends finish a race, who came second?'


def clear_learned():
    limits._windows.clear(); limits._thinks.clear()


class WantsThinkingTests(SimpleTestCase):
    def test_auto_thinks_only_for_hard_general_or_travel_questions(self):
        for query, scope in ((PUZZLE, 'general'), ('Plan a 4-day motorbike trip from Bengaluru with hills', 'travel'),
                             ('Give me a day-by-day itinerary for Coorg', 'general'),
                             ('Which order of stops minimises riding hours?', 'travel'),
                             ('Leave 7 08 visit 3 4 5 6 return 18', 'general'), ('x ' * 300, 'general')):
            with self.subTest(query=query[:40]):
                self.assertTrue(wants_thinking(query, scope))
        for query, scope in (('How much did I spend on fuel?', 'general'), ('What does SIP mean?', 'general'),
                             ('Hello', 'travel'), (PUZZLE, 'finance'), (PUZZLE, 'bank_statements'), (PUZZLE, 'documents')):
            with self.subTest(query=query, scope=scope):
                self.assertFalse(wants_thinking(query, scope))

    def test_owner_setting_turns_it_on_off_and_rejects_unknown_values(self):
        with override_settings(ALFRED_LOCAL_AI_THINKING='off'):
            self.assertFalse(wants_thinking(PUZZLE, 'general'))
        with override_settings(ALFRED_LOCAL_AI_THINKING='ON'):
            self.assertTrue(wants_thinking('Hello', 'general'))
            self.assertFalse(wants_thinking('Hello', 'finance'))  # owner records never think
        with override_settings(ALFRED_LOCAL_AI_THINKING='always'):
            self.assertFalse(wants_thinking(PUZZLE, 'general'))


class CapabilityTests(SimpleTestCase):
    def setUp(self):
        clear_learned(); self.addCleanup(clear_learned)

    def test_thinking_capability_is_read_with_the_window_once_per_digest(self):
        client = Mock(model='synthetic-local:9b')
        client._request.return_value = {'model_info': {'qwen3.context_length': 16384}, 'capabilities': ['completion', 'thinking']}
        self.assertFalse(limits.supports_thinking(client))  # unknown until learned
        limits.learn_window(client, 'a' * 64); limits.learn_window(client, 'a' * 64)
        self.assertTrue(limits.supports_thinking(client)); self.assertEqual(client._request.call_count, 1)
        client._request.return_value = {'model_info': {'qwen3.context_length': 16384}, 'capabilities': ['completion']}
        limits.learn_window(client, 'b' * 64)
        self.assertFalse(limits.supports_thinking(client))
        client._request.return_value = {'model_info': {}, 'capabilities': 'thinking'}
        limits.learn_window(client, 'c' * 64)
        self.assertFalse(limits.supports_thinking(client))


class ReasonerThinkingTests(SimpleTestCase):
    def setUp(self):
        clear_learned(); self.addCleanup(clear_learned)
        self.reasoner = OllamaReasoner(); self.bodies = []

    def run_reason(self, payload, thinks=True, content='Synthetic answer.', **kwargs):
        def request(method, path, body=None, *, deadline=None):
            self.bodies.append(body)
            return dict(model=self.reasoner.model, done=True,
                        message=dict(role='assistant', content=content, thinking='synthetic hidden steps'))
        limits._thinks[self.reasoner.model] = ('a' * 64, thinks)
        with patch.object(self.reasoner, '_digest', return_value='a' * 64), patch.object(self.reasoner, '_request', side_effect=request):
            return self.reasoner.reason(payload, deadline=time.monotonic() + 5, **kwargs)

    def test_thinking_gets_its_own_budget_and_hidden_steps_are_dropped(self):
        answer = self.run_reason({'query': PUZZLE}, max_output_tokens=512, think=True)
        self.assertEqual(answer, 'Synthetic answer.'); self.assertNotIn('hidden', answer)
        self.assertTrue(self.bodies[0]['think']); self.assertTrue(self.reasoner.thought)
        self.assertEqual(self.bodies[0]['options']['num_predict'], 512 + 3072)
        with override_settings(ALFRED_LOCAL_AI_THINKING_TOKENS=8000):
            self.run_reason({'query': PUZZLE}, max_output_tokens=512, think=True)
        self.assertEqual(self.bodies[1]['options']['num_predict'], 8512)

    def test_no_thinking_without_the_capability_the_request_or_room_for_it(self):
        self.run_reason({'query': PUZZLE}, thinks=False, think=True)
        self.run_reason({'query': PUZZLE}, thinks=True)
        # Sources that fit the answer budget but not answer plus thinking keep the sources and drop the thinking.
        fits_answer_only = 'x' * (limits.context_bytes(8192, 256) - 200)
        self.run_reason({'query': PUZZLE, 'sources': [{'ref': 'synthetic', 'data': fits_answer_only}]}, think=True)
        for body in self.bodies:
            self.assertFalse(body['think']); self.assertEqual(body['options']['num_predict'], 256)
        self.assertFalse(self.reasoner.thought)

    def test_invalid_flag_and_empty_answer_after_thinking_are_refused(self):
        with self.assertRaises(ValueError):
            self.run_reason({'query': PUZZLE}, think='yes')
        with self.assertRaises(EmbeddingUnavailable):
            self.run_reason({'query': PUZZLE}, think=True, content='')


class HybridAnswerThinkingTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-thinking-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root / 'vault'), ALFRED_ABUSE_THROTTLE_DIR=str(root / 'limits'),
                                            ALFRED_MEMORY_MOCK_REASONING=False, ALFRED_MEMORY_OPENAI_AUTHORIZED=False))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=SyntheticEmbeddings()))
        self.store = MemoryStore(root / 'vault')
        self.user = get_user_model().objects.create_user(username='synthetic-thinking-owner')
        self.local = Mock(); self.local.reason.return_value = 'Synthetic AI hypothesis.'

    def test_hard_questions_ask_to_think_and_report_whether_it_happened(self):
        result = hybrid_answer(self.store, self.user, 'What is a monsoon?', local=self.local)
        self.assertNotIn('think', self.local.reason.call_args.kwargs); self.assertFalse(result['local_thinking'])
        self.local.thought = True
        result = hybrid_answer(self.store, self.user, PUZZLE, local=self.local)
        self.assertIs(self.local.reason.call_args.kwargs['think'], True); self.assertTrue(result['local_thinking'])
        self.assertEqual(result['local_output_token_limit'], 384)  # the answer budget itself is unchanged


class StreamThinkingTests(SimpleTestCase):
    def setUp(self):
        clear_learned(); self.addCleanup(clear_learned)

    def frames(self, model, *thinking_then_text):
        items = [dict(model=model, done=False, message=dict(role='assistant', content='', thinking=step))
                 for step in thinking_then_text[:-1]]
        items += [dict(model=model, done=False, message=dict(role='assistant', content=thinking_then_text[-1])),
                  dict(model=model, done=True, done_reason='stop', message=dict(role='assistant', content=''))]
        return b''.join((json.dumps(item) + '\n').encode() for item in items)

    def test_thinking_frames_announce_once_and_never_reach_the_answer_or_preview(self):
        stream = LocalChatStream(lambda s: None, lambda exc: {}, lambda: None)
        reasoner = OllamaReasoner(stream=stream)
        limits._thinks[reasoner.model] = ('a' * 64, True)
        connection = Mock(); connection.getresponse.return_value = WireResponse(self.frames(reasoner.model, 'step one', 'step two', 'Ravi first.'))
        with patch.object(reasoner, '_digest', return_value='a' * 64), \
                patch('apps.ml_engine.services.local_chat_stream.HTTPConnection', return_value=connection):
            answer = reasoner.reason({'query': PUZZLE, 'sources': []}, deadline=time.monotonic() + 30, think=True)
        self.assertEqual(answer, 'Ravi first.')
        self.assertTrue(json.loads(connection.request.call_args.kwargs['body'])['think'])
        events = []
        while not stream.queue.empty(): events.append(stream.queue.get_nowait())
        self.assertEqual(events, [{'type': 'thinking'}, {'type': 'delta', 'text': 'Ravi first.'}])
        self.assertNotIn('step', str(events))

    def test_thinking_the_request_did_not_ask_for_is_rejected(self):
        stream = LocalChatStream(lambda s: None, lambda exc: {}, lambda: None)
        reasoner = OllamaReasoner(stream=stream)
        connection = Mock(); connection.getresponse.return_value = WireResponse(self.frames(reasoner.model, 'unasked', 'Answer.'))
        with patch.object(reasoner, '_digest', return_value='a' * 64), \
                patch('apps.ml_engine.services.local_chat_stream.HTTPConnection', return_value=connection), \
                self.assertRaises(GenerationIncomplete):
            reasoner.reason({'query': 'Synthetic', 'sources': []}, deadline=time.monotonic() + 30)
