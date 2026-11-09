"""Opt-in actual Ollama acceptance, with only synthetic local conversations."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ml_engine.services.conversation_history import ConversationHistory
from apps.ml_engine.services.persistent_memory import MemoryStore


@skipUnless(os.environ.get('ALFRED_RUN_LOCAL_AI_ACCEPTANCE') == 'true', 'Requires explicit real local Ollama acceptance')
class LocalConversationAcceptance(TestCase):
    def test_actual_local_model_remembers_synthetic_turn_after_vault_reopen(self):
        with TemporaryDirectory(prefix='alfred-local-dialogue-synthetic-') as directory, override_settings(
                ALFRED_MEMORY_DIR=str(Path(directory)/'vault'), ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True,
                ALFRED_MEMORY_OPENAI_AUTHORIZED=False, ALFRED_MEMORY_CLOUD_AUTHORIZED=False):
            owner = get_user_model().objects.create_user(username='synthetic-real-local-dialogue')
            history = ConversationHistory(MemoryStore(Path(directory)/'vault'))
            history.configure(owner, enabled=True, consent=True, days=1)
            record = history.create(owner, 'Synthetic local continuity acceptance')
            self.client.force_login(owner)
            def ask(question, revision):
                response = self.client.post('/api/ai/personal-insights/', {
                    'query': question, 'scope': 'general', 'cloud_consent': False,
                    'conversation_id': record['id'], 'conversation_revision': revision, 'request_id': uuid4().hex,
                }, content_type='application/json')
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()['provider'], 'ollama')
                return response.json()
            first = ask("In this fictional story the robot's favorite color is cobalt. Acknowledge that briefly.", 0)
            reopened = ConversationHistory(MemoryStore(Path(directory)/'vault'))
            self.assertEqual(len(reopened.get(owner, record['id'])['turns']), 1)
            second = ask("What was the fictional robot's favorite color?", first['conversation']['revision'])
            self.assertIn('cobalt', second['answer'].lower())
            self.assertEqual(second['conversation_context_turns'], 1)
            self.assertEqual(reopened.store.list_memories(owner), [])
