"""Opt-in actual Waitress HTTP and Ollama streaming; synthetic account and vault only."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.handlers.wsgi import WSGIHandler
from django.test import TransactionTestCase, override_settings
import requests

from alfred_ai.services.native_web import create_native_server
from apps.ml_engine.services.local_chat_stream import LocalChatStream
from apps.ml_engine.services.persistent_memory import MemoryStore
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches


@skipUnless(os.environ.get('ALFRED_RUN_LOCAL_AI_ACCEPTANCE') == 'true','Requires explicit actual local inference acceptance')
class NativeLocalStreamAcceptance(TransactionTestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-native-stream-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits'),
            ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,ALFRED_MEMORY_OPENAI_AUTHORIZED=False,
            ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALLOWED_HOSTS=['127.0.0.1','testserver']))
        self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='synthetic-native-stream')
        self.client.force_login(self.owner); self.streams = []
        def stream(*args,**kwargs):
            result = LocalChatStream(*args,**kwargs); self.streams.append(result); return result
        self.enterContext(patch('apps.ml_engine.api.chat_stream.LocalChatStream',side_effect=stream))
        self.server = create_native_server(WSGIHandler(),0)
        self.server_thread = Thread(target=self.server.run,daemon=True); self.server_thread.start()
        self.base = 'http://127.0.0.1:'+str(self.server.effective_port)
        self.session = requests.Session(); self.session.trust_env = False
        self.session.cookies.set(settings.SESSION_COOKIE_NAME,self.client.session.session_key)
        page = self.session.get(self.base+'/ai/insights/',timeout=10); page.raise_for_status()
        self.session.headers['X-CSRFToken'] = self.session.cookies[settings.CSRF_COOKIE_NAME]

    def tearDown(self):
        for stream in self.streams:
            stream.close(); stream.worker.join(timeout=3)
            self.assertFalse(stream.worker.is_alive())
        self.session.close(); self.server.task_dispatcher.shutdown(timeout=3)
        self.server.asyncore.close_all(self.server._map); self.server_thread.join(timeout=3)
        super().tearDown()

    def post(self,query,style='concise'):
        return self.session.post(self.base+'/api/ai/personal-insights/stream/',
            json=dict(query=query,scope='general',cloud_consent=False,answer_style=style),stream=True,timeout=(3,35))

    def test_actual_native_stream_delivers_tokens_then_a_validated_answer(self):
        started = time.monotonic(); first_token = None; final = None; events = []
        with self.post('Give a short friendly greeting.') as response:
            response.raise_for_status(); self.assertIn('no-store',response.headers['Cache-Control'])
            for raw in response.iter_lines(chunk_size=1):
                event = json.loads(raw); events.append(event['type'])
                if event['type']=='delta' and first_token is None: first_token = time.monotonic()-started
                self.assertNotEqual(event['type'],'error',event)
                if event['type']=='final': final = event['result']
        self.assertIsNotNone(first_token); self.assertIsNotNone(final)
        self.assertEqual(final['provider'],'ollama'); self.assertFalse(final['narrative_withheld'])
        print('ACTUAL_SYNTHETIC_NATIVE_STREAM '+json.dumps(dict(seconds=round(time.monotonic()-started,3),
            first_token_seconds=round(first_token,3),events=len(events),answer_bytes=len(final['answer'].encode()))))

    def test_actual_native_disconnect_stops_local_generation_without_retaining_a_turn(self):
        response = self.post('Tell a long fictional story about a robot learning to dance in rain. Label it fiction.','detailed')
        response.raise_for_status(); preview = False
        for raw in response.iter_lines(chunk_size=1):
            event = json.loads(raw)
            self.assertNotEqual(event['type'],'error',event)
            self.assertNotEqual(event['type'],'final','Cancellation must happen during active generation')
            if event['type']=='delta': preview = True; break
        self.assertTrue(preview)
        stream = self.streams[-1]
        self.assertTrue(stream.worker.is_alive(),'Stop must interrupt a running inference')
        started = time.monotonic(); response.close()
        stream.worker.join(timeout=3)
        self.assertFalse(stream.worker.is_alive(),'Native client disconnect must close the Ollama transport promptly')
        self.assertTrue(stream.cancelled.is_set())
        store = MemoryStore(settings.ALFRED_MEMORY_DIR)
        with store._transaction() as db:
            for table in ('conversations','conversation_policies','memories','events'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        print('ACTUAL_SYNTHETIC_NATIVE_CANCEL '+json.dumps(dict(seconds=round(time.monotonic()-started,3),
            worker_stopped=True,retained_turns=0)))
