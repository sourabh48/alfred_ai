"""Opt-in actual Ollama acceptance, with only synthetic local conversations."""
import os
import json
import time
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
    def test_actual_local_page_followup_without_history_retention(self):
        with TemporaryDirectory(prefix='alfred-local-page-synthetic-') as directory, override_settings(
                ALFRED_MEMORY_DIR=str(Path(directory)/'vault'),ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,
                ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_CLOUD_AUTHORIZED=False):
            owner = get_user_model().objects.create_user(username='synthetic-real-local-page')
            self.client.force_login(owner)
            first_query = 'In this fictional story the robot likes the color cobalt. Acknowledge briefly.'
            first = self.client.post('/api/ai/personal-insights/',dict(query=first_query,cloud_consent=False),content_type='application/json')
            self.assertEqual(first.status_code,200,first.content)
            self.assertEqual(first.json()['provider'],'ollama')
            snippet = first.json()['answer'].encode()[:768].decode(errors='ignore')
            second = self.client.post('/api/ai/personal-insights/',dict(query='What color did the fictional robot like?',
                cloud_consent=False,page_context=[dict(role='user',content=first_query),dict(role='assistant',content=snippet)]),content_type='application/json')
            self.assertEqual(second.status_code,200,second.content)
            self.assertIn('cobalt',second.json()['answer'].lower())
            self.assertEqual(second.json()['conversation_context_turns'],1)
            store = MemoryStore(Path(directory)/'vault')
            with store._transaction() as db:
                for table in ('conversations','conversation_policies','memories','events'):
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)

    def test_actual_local_answer_styles_respect_server_budgets(self):
        with TemporaryDirectory(prefix='alfred-local-styles-synthetic-') as directory, override_settings(
                ALFRED_MEMORY_DIR=str(Path(directory)/'vault'), ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,
                ALFRED_MEMORY_OPENAI_AUTHORIZED=False, ALFRED_MEMORY_CLOUD_AUTHORIZED=False):
            owner = get_user_model().objects.create_user(username='synthetic-real-local-styles')
            self.client.force_login(owner)
            for style, limit in (('concise',192),('detailed',1024)):
                started = time.monotonic()
                response = self.client.post('/api/ai/personal-insights/', {
                    'query':'Tell a fictional story about a robot called Pavo who learns to dance in the rain. Clearly label it fiction.',
                    'scope':'general','answer_style':style,'cloud_consent':False,
                },content_type='application/json')
                self.assertEqual(response.status_code,200,response.content)
                result = response.json()
                self.assertEqual(result['provider'],'ollama')
                self.assertEqual(result['answer_style'],style)
                self.assertEqual(result['local_output_token_limit'],limit)
                self.assertLessEqual(len(result['answer'].encode()),8192)
                self.assertFalse(result['narrative_withheld'])
                print('SYNTHETIC_LOCAL_STYLE '+json.dumps(dict(style=style,token_limit=limit,
                    seconds=round(time.monotonic()-started,3),words=len(result['answer'].split()),
                    bytes=len(result['answer'].encode()),sources=len(result['sources']))))
            self.assertEqual(MemoryStore(Path(directory)/'vault').list_memories(owner),[])

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
            renamed = reopened.rename(owner,record['id'],'Synthetic renamed continuity',first['conversation']['revision'])
            second = ask("What was the fictional robot's favorite color?", renamed['revision'])
            if 'cobalt' not in second['answer'].lower():
                print('SYNTHETIC_FICTION_CONTINUITY '+json.dumps(dict(first=first['answer'],
                    second=second['answer'],context_turns=second['conversation_context_turns'])))
            self.assertIn('cobalt', second['answer'].lower())
            self.assertEqual(second['conversation_context_turns'], 1)
            self.assertEqual(reopened.get(owner,record['id'])['title'],'Synthetic renamed continuity')
            self.assertEqual(reopened.store.list_memories(owner), [])
