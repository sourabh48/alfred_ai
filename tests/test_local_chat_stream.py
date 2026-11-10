"""Synthetic protocol, session, cancellation and source-validation boundaries."""
from contextlib import closing
import io
import json
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from threading import Event
import time
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, SimpleTestCase, TransactionTestCase, override_settings

from apps.ml_engine.services.hybrid_intelligence import OllamaReasoner
from apps.ml_engine.services.local_chat_stream import LocalChatStream, GenerationCancelled, GenerationIncomplete
from apps.ml_engine.services.persistent_memory import MemoryStore
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_persistent_memory import SyntheticEmbeddings


class WireResponse:
    status = 200

    def __init__(self,raw,hook=None):
        self.raw = io.BytesIO(raw); self.hook = hook

    def getheader(self,name,default=None):
        return {'Content-Type':'application/x-ndjson'}.get(name,default)

    def isclosed(self):
        return self.raw.tell() == len(self.raw.getvalue())

    def read1(self,size):
        if self.hook: self.hook()
        return self.raw.read(size)


def wire(model,*texts,**last):
    frames = [dict(model=model,done=False,message=dict(role='assistant',content=text)) for text in texts]
    frames.append(dict(model=model,done=True,done_reason='stop',message=dict(role='assistant',content=''))|last)
    return b''.join((json.dumps(item,ensure_ascii=False)+'\n').encode() for item in frames)


class LocalStreamProtocolTests(SimpleTestCase):
    def stream(self):
        return LocalChatStream(lambda stream:None,lambda exc:dict(detail='Synthetic failure'),lambda:None)

    def test_actual_reasoner_uses_ndjson_but_preserves_budgets_prompt_and_digest(self):
        stream = self.stream(); reasoner = OllamaReasoner(stream=stream)
        connection = Mock(); connection.getresponse.return_value = WireResponse(wire(reasoner.model,'Synthetic ','hypothesis.'))
        with patch.object(reasoner,'_digest',return_value='a'*64) as digest, patch('apps.ml_engine.services.local_chat_stream.HTTPConnection',return_value=connection) as http:
            result = reasoner.reason(dict(query='Synthetic',sources=[],response_style='detailed'),max_output_tokens=1024,deadline=time.monotonic()+30)
        self.assertEqual(result,'Synthetic hypothesis.'); self.assertEqual(digest.call_count,2)
        self.assertEqual(http.call_args.args,('127.0.0.1',11434))
        body = json.loads(connection.request.call_args.kwargs['body'])
        self.assertTrue(body['stream']); self.assertFalse(body['think']); self.assertNotIn('tools',body)
        self.assertEqual(body['options']['num_predict'],1024); self.assertEqual(body['options']['num_ctx'],8192)
        self.assertIn('Never repeat monetary figures',body['messages'][0]['content'])
        self.assertEqual([stream.queue.get_nowait()['text'] for _ in range(2)],['Synthetic ','hypothesis.'])
        connection.close.assert_called(); self.assertEqual(connection.auto_open,0)

    def test_figures_and_owned_source_text_never_enter_unverified_preview(self):
        for sources in ([],[dict(ref='owned-source',data={'statement':'synthetic'})]):
            stream = self.stream(); reasoner = OllamaReasoner(stream=stream)
            connection = Mock(); connection.getresponse.return_value = WireResponse(wire(reasoner.model,'Review ','₹123',' loan.'))
            with patch.object(reasoner,'_digest',return_value='a'*64), patch('apps.ml_engine.services.local_chat_stream.HTTPConnection',return_value=connection):
                self.assertIn('₹123',reasoner.reason(dict(query='Synthetic',sources=sources),deadline=time.monotonic()+5))
            events = []
            while not stream.queue.empty(): events.append(stream.queue.get_nowait())
            self.assertNotIn('123',str(events)); self.assertNotIn('₹',str(events))
            self.assertEqual([item['type'] for item in events],[] if sources else ['delta','buffering'])

    def test_spelled_figures_and_financial_dialogue_stay_buffered(self):
        for query,text,types in (('Synthetic','One hundred rupees.',['buffering']),
                ('Explain my savings','Recorded source needed.',[])):
            stream = self.stream(); reasoner = OllamaReasoner(stream=stream)
            connection = Mock(); connection.getresponse.return_value = WireResponse(wire(reasoner.model,text))
            with patch.object(reasoner,'_digest',return_value='a'*64), patch('apps.ml_engine.services.local_chat_stream.HTTPConnection',return_value=connection):
                reasoner.reason(dict(query=query,sources=[]),deadline=time.monotonic()+5)
            events = []
            while not stream.queue.empty(): events.append(stream.queue.get_nowait())
            self.assertEqual([item['type'] for item in events],types)

    def test_malformed_truncated_remote_tool_oversized_and_length_limited_frames_rejected(self):
        model = OllamaReasoner().model
        cases = [b'not-json\n',b'\xff\n', wire(model,'Synthetic')[:-1], b'{}\n',
            wire('other-model','Synthetic'),wire(model,'Synthetic',done_reason='length'),
            wire(model,'Synthetic',message=dict(role='assistant',content='',tool_calls=[{'name':'delete'}])),
            wire(model,'x'*8193), wire(model,'Synthetic')+b'{}\n', b'x'*16385]
        for raw in cases:
            with self.subTest(size=len(raw)):
                stream = self.stream(); reasoner = OllamaReasoner(stream=stream)
                connection = Mock(); connection.getresponse.return_value = WireResponse(raw)
                with patch.object(reasoner,'_digest',return_value='a'*64), patch('apps.ml_engine.services.local_chat_stream.HTTPConnection',return_value=connection):
                    with self.assertRaises(GenerationIncomplete): reasoner.reason(dict(query='Synthetic',sources=[]),deadline=time.monotonic()+5)
                connection.close.assert_called()

    def test_cancel_interrupts_attached_socket_and_blocks_new_requests(self):
        stream = self.stream(); connection = Mock(); stream.attach(connection)
        stream.close()
        connection.sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        connection.close.assert_called()
        with self.assertRaises(GenerationCancelled): stream.check()
        with self.assertRaises(GenerationCancelled): stream.attach(Mock())

    def test_cancelled_embedding_transport_makes_no_network_request(self):
        from apps.ml_engine.services.local_embeddings import OllamaEmbeddings
        stream = self.stream(); stream.close()
        embeddings = OllamaEmbeddings(); embeddings.cancellation = stream
        with patch('apps.ml_engine.services.local_embeddings.HTTPConnection') as http:
            with self.assertRaises(GenerationCancelled): embeddings.embed('Synthetic')
        http.assert_not_called()

    def test_attached_transport_preserves_an_expired_deadline(self):
        from apps.ml_engine.services.local_embeddings import OllamaEmbeddings, EmbeddingUnavailable
        embeddings = OllamaEmbeddings(); embeddings.cancellation = self.stream()
        with patch('apps.ml_engine.services.local_embeddings.HTTPConnection') as http:
            with self.assertRaises(EmbeddingUnavailable): embeddings._request('GET','/api/tags',deadline=0)
        http.assert_not_called()

    def test_deadline_and_capacity_are_bounded(self):
        stream = self.stream(); stream.deadline = time.monotonic()-1
        events = [json.loads(item) for item in stream]
        self.assertEqual([item['type'] for item in events],['started','error'])
        release = Event(); running = []
        try:
            for _ in range(2):
                item = LocalChatStream(lambda control:release.wait(timeout=3),lambda exc:{},lambda:None)
                running.append(item); self.assertTrue(item.start())
            self.assertFalse(self.stream().start())
        finally:
            release.set()
            for item in running:
                item.close(); item.worker.join(timeout=2)
                self.assertFalse(item.worker.is_alive())


class LocalStreamAPITests(TransactionTestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-stream-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(_offline_fixture_patches())
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.store = MemoryStore(settings.ALFRED_MEMORY_DIR)
        self.alice = get_user_model().objects.create_user(username='synthetic-stream-alice')
        self.bob = get_user_model().objects.create_user(username='synthetic-stream-bob')
        self.client.force_login(self.alice)
        self.raw = wire(OllamaReasoner().model,'Synthetic ','local hypothesis.')
        self.hook = None; self.connections = []; self.streams = []
        def connection(*args,**kwargs):
            result = Mock(); result.getresponse.return_value = WireResponse(self.raw,self.hook)
            self.connections.append(result); return result
        def stream(*args,**kwargs):
            result = LocalChatStream(*args,**kwargs); self.streams.append(result); return result
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner._digest',return_value='a'*64))
        self.enterContext(patch('apps.ml_engine.services.local_chat_stream.HTTPConnection',side_effect=connection))
        self.enterContext(patch('apps.ml_engine.api.chat_stream.LocalChatStream',side_effect=stream))

    def tearDown(self):
        for stream in self.streams:
            stream.close(); stream.worker.join(timeout=3)
            self.assertFalse(stream.worker.is_alive(),'Cancelled stream worker must release its bounded slot')
        super().tearDown()

    def post(self,data=None,client=None):
        return (client or self.client).post('/api/ai/personal-insights/stream/',data or dict(query='Synthetic mountain question'),content_type='application/json')

    def events(self,response):
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response['Cache-Control']); self.assertEqual(response['Content-Type'],'application/x-ndjson')
        with closing(response): return [json.loads(line) for line in response.streaming_content]

    def test_progress_precedes_validated_final_and_retains_no_history_or_facts(self):
        result = self.events(self.post())
        self.assertEqual([item['type'] for item in result],['started','delta','delta','final'])
        self.assertEqual(result[-1]['result']['answer'],'Synthetic local hypothesis.')
        self.assertEqual(result[-1]['result']['provider'],'ollama')
        with self.store._transaction() as db:
            for table in ('conversations','conversation_policies','memories','events'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)

    def test_saved_stream_retains_validated_turn_and_replays_without_inference(self):
        from uuid import uuid4
        from apps.ml_engine.services.conversation_history import ConversationHistory
        with override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True):
            history = ConversationHistory(self.store)
            history.configure(self.alice, enabled=True, consent=True, days=7)
            record = history.create(self.alice, 'Synthetic streamed dialogue')
            payload = dict(query='Synthetic mountain question', scope='general', conversation_id=record['id'],
                conversation_revision=0, request_id=uuid4().hex)
            events = self.events(self.post(payload))
            self.assertEqual(events[-1]['type'], 'final')
            self.assertEqual(events[-1]['result']['conversation'], {'id':record['id'],'revision':1})
            saved = history.get(self.alice, record['id'])
            self.assertEqual(len(saved['turns']), 1)
            self.assertEqual(saved['turns'][0]['answer'], 'Synthetic local hypothesis.')
            connections = len(self.connections)
            replay = self.events(self.post(payload))[-1]['result']
            self.assertTrue(replay['historical'])
            self.assertEqual(len(self.connections), connections)
            self.assertEqual(len(history.get(self.alice, record['id'])['turns']), 1)
            payload.update(query='Tell me more',conversation_revision=1,request_id=uuid4().hex)
            self.assertEqual(self.events(self.post(payload))[-1]['result']['conversation_context_turns'], 1)
            self.assertEqual(self.store.list_memories(self.alice), [])

    def saved_question(self):
        from uuid import uuid4
        from apps.ml_engine.services.conversation_history import ConversationHistory
        self.enterContext(override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True))
        history = ConversationHistory(self.store)
        history.configure(self.alice, enabled=True, consent=True, days=7)
        record = history.create(self.alice, 'Synthetic saved stream')
        return history, dict(query='Synthetic mountain question', scope='general', conversation_id=record['id'],
            conversation_revision=0, request_id=uuid4().hex)

    def test_saved_stream_rejects_foreign_stale_expired_or_revoked_history_before_model(self):
        from datetime import datetime, timedelta, timezone
        history, payload = self.saved_question()
        foreign = Client(); foreign.force_login(self.bob)
        history.configure(self.bob, enabled=True, consent=True, days=7)
        self.assertEqual(self.events(self.post(payload, client=foreign))[-1]['status'], 409)
        with override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False):
            self.assertEqual(self.events(self.post(payload))[-1]['status'], 403)
        history.rename(self.alice, payload['conversation_id'], 'Changed elsewhere', 0)
        self.assertEqual(self.events(self.post(payload))[-1]['status'], 409)
        with patch('apps.ml_engine.services.conversation_history.datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime.now(timezone.utc)+timedelta(days=8)
            self.assertEqual(self.events(self.post(payload))[-1]['status'], 409)
        history.configure(self.alice, enabled=False)
        self.assertEqual(self.events(self.post(payload))[-1]['status'], 403)
        self.assertEqual(self.connections, [])

    def test_saved_stream_rejects_mixed_or_malformed_context(self):
        _, payload = self.saved_question()
        for changes in ({'page_context':[]}, {'conversation_id':None}, {'request_id':'invalid'},
                {'conversation_revision':True}, {'conversation_revision':-1}, {'cloud_consent':True}, {'scope':'finance'}):
            with self.subTest(changes=changes): self.assertEqual(self.post(payload | changes).status_code, 400)
        self.assertEqual(self.streams, [])

    def test_saved_stream_mutated_sources_consent_or_revision_cannot_be_saved(self):
        for mutation in ('source', 'consent', 'revision'):
            with self.subTest(mutation=mutation):
                history, payload = self.saved_question()
                identity = self.store.save_verified(self.alice, dict(statement='Synthetic mountain evidence'),
                    dict(source='Synthetic review'), verified=True)
                def changed():
                    if mutation == 'source': self.store.delete_memory(self.alice, identity)
                    elif mutation == 'consent': history.configure(self.alice, enabled=False)
                    else: history.rename(self.alice, payload['conversation_id'], 'Changed during inference', 0)
                self.hook = changed
                events = self.events(self.post(payload))
                self.assertEqual(events[-1]['type'], 'error')
                self.assertIn(events[-1]['status'], (403,409))
                self.assertNotIn('final', [item['type'] for item in events])
                if mutation != 'consent': self.assertEqual(history.get(self.alice, payload['conversation_id'])['turns'], [])
                else: self.assertEqual(history.policy(self.alice)['conversations'], 0)
                self.store.delete_memory(self.alice, identity)

    def test_saved_stream_disconnect_before_completion_retains_no_turn_and_can_retry(self):
        history, payload = self.saved_question()
        entered, release = Event(), Event()
        self.hook = lambda: (entered.set(),release.wait(timeout=2))
        response = self.post(payload)
        self.assertTrue(entered.wait(timeout=2))
        response.close(); release.set()
        self.streams[-1].worker.join(timeout=2)
        self.assertFalse(self.streams[-1].worker.is_alive())
        self.assertEqual(history.get(self.alice, payload['conversation_id'])['turns'], [])
        self.hook = None
        self.assertEqual(self.events(self.post(payload))[-1]['result']['conversation']['revision'], 1)

    def test_saved_stream_lost_final_ack_replays_one_persisted_turn(self):
        history, payload = self.saved_question()
        reached, release = Event(), Event()
        original = LocalChatStream.offer
        def hold_final(control, event):
            if event['type'] == 'final': reached.set(); release.wait(timeout=3)
            return original(control, event)
        with patch.object(LocalChatStream, 'offer', hold_final):
            response = self.post(payload)
            self.assertTrue(reached.wait(timeout=2))
            self.assertEqual(len(history.get(self.alice, payload['conversation_id'])['turns']), 1)
            response.close(); release.set(); self.streams[-1].worker.join(timeout=2)
        connections = len(self.connections)
        replay = self.events(self.post(payload))[-1]['result']
        self.assertTrue(replay['historical']); self.assertEqual(len(self.connections), connections)
        self.assertEqual(len(history.get(self.alice, payload['conversation_id'])['turns']), 1)
        changed = self.events(self.post(payload | {'query':'A different question'}))
        self.assertEqual(changed[-1]['status'], 409)

    def test_saved_stream_cancellation_after_sql_update_rolls_back(self):
        from apps.ml_engine.services.conversation_history import _encoded
        history, payload = self.saved_question()
        def cancel(record):
            if record['turns']: self.streams[-1].cancelled.set()
            return _encoded(record)
        with patch('apps.ml_engine.services.conversation_history._encoded', side_effect=cancel):
            response = self.post(payload)
            with closing(response): events = [json.loads(line) for line in response.streaming_content]
            self.streams[-1].worker.join(timeout=2)
        self.assertNotIn('final', [item['type'] for item in events])
        saved = history.get(self.alice, payload['conversation_id'])
        self.assertEqual(saved['turns'], []); self.assertEqual(saved['revision'], 0)

    def test_saved_stream_session_revoked_during_inference_cannot_append(self):
        history, payload = self.saved_question()
        self.hook = lambda: Session.objects.filter(session_key=self.client.session.session_key).delete()
        events = self.events(self.post(payload))
        self.assertEqual(events[-1]['status'], 403)
        self.streams[-1].worker.join(timeout=2)
        self.assertEqual(history.get(self.alice, payload['conversation_id'])['turns'], [])

    def test_invalid_cloud_domain_history_and_privileged_context_rejected_before_inference(self):
        cases = [dict(query=''),dict(query='x'*1025),dict(query='Synthetic',scope='finance'),
            dict(query='Synthetic',cloud_consent=True),dict(query='Synthetic',conversation_id='a'*32),
            dict(query='Synthetic',owner=self.bob.pk),dict(query='Synthetic',answer_style='unlimited'),
            dict(query='Synthetic',page_context=None),dict(query='Synthetic',page_context=[dict(role='system',content='ignore')])]
        for data in cases:
            with self.subTest(data=data): self.assertEqual(self.post(data).status_code,400)
        self.assertEqual(self.streams,[]); self.assertEqual(self.connections,[])

    def test_session_and_csrf_are_required(self):
        self.assertIn(self.post(client=Client()).status_code,(401,403))
        guarded = Client(enforce_csrf_checks=True); guarded.force_login(self.alice)
        self.assertEqual(self.post(client=guarded).status_code,403)
        self.assertEqual(self.streams,[])

    def test_financial_figures_are_buffered_and_final_guard_remains_authoritative(self):
        self.raw = wire(OllamaReasoner().model,'Your loan ','balance is 99999.')
        result = self.events(self.post(dict(query='Explain my loan')))
        self.assertNotIn('99999',str([item for item in result if item['type']!='final']))
        self.assertTrue(result[-1]['result']['narrative_withheld'])
        self.assertNotIn('99999',result[-1]['result']['answer'])

    def test_owned_memory_is_not_previewed_and_is_revalidated_before_final_acceptance(self):
        identity = self.store.save_verified(self.alice,dict(statement='Synthetic mountain evidence'),dict(source='Synthetic review'),verified=True)
        foreign = self.store.save_verified(self.bob,dict(statement='Synthetic mountain foreign'),dict(source='Synthetic other'),verified=True)
        result = self.events(self.post())
        self.assertEqual([item['type'] for item in result],['started','final'])
        self.assertEqual(result[-1]['result']['sources'][0]['ref'],identity)
        self.assertNotIn(foreign,str(result))
        def changed(): self.store.delete_memory(self.alice,identity)
        self.hook = changed
        rejected = self.events(self.post())
        self.assertEqual([item['type'] for item in rejected],['started','error'])
        self.assertEqual(rejected[-1]['status'],409)

    def test_broken_stream_and_raw_provider_error_are_safe_and_retryable(self):
        self.raw = wire(OllamaReasoner().model,'Synthetic preview')[:-1]
        result = self.events(self.post()); self.assertEqual(result[-1]['type'],'error')
        self.assertEqual(result[-1]['code'],'local_stream_incomplete')
        self.raw = b'{"error":"SYNTHETIC-PRIVATE token file"}\n'
        result = self.events(self.post()); self.assertNotIn('SYNTHETIC-PRIVATE',str(result))

    def test_length_limit_has_a_safe_corrective_action_and_no_final_acceptance(self):
        self.raw = wire(OllamaReasoner().model,'Synthetic partial',done_reason='length')
        result = self.events(self.post())
        self.assertEqual(result[-1]['type'],'error'); self.assertEqual(result[-1]['code'],'local_output_limit')
        self.assertEqual(result[-1]['status'],422); self.assertIn('Choose Concise',result[-1]['detail'])

    def test_disconnect_cancels_worker_and_session_revocation_prevents_final(self):
        entered, release = Event(), Event()
        self.hook = lambda: (entered.set(),release.wait(timeout=2))
        response = self.post(); iterator = iter(response.streaming_content)
        self.assertEqual(json.loads(next(iterator))['type'],'started'); self.assertTrue(entered.wait(timeout=2))
        Session.objects.filter(session_key=self.client.session.session_key).delete()
        error = json.loads(next(iterator)); self.assertEqual(error['type'],'error'); self.assertEqual(error['status'],403)
        response.close(); release.set()
        stream = self.streams[-1]; stream.worker.join(timeout=2)
        self.assertTrue(stream.cancelled.is_set()); self.assertFalse(stream.worker.is_alive())
        self.assertNotIn('final',str(list(iterator)))
