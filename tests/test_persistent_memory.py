from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import sqlite3
import subprocess
import sys
import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, SimpleTestCase

from apps.ml_engine.services.local_embeddings import OllamaEmbeddings, EmbeddingUnavailable, validate_vector
from apps.ml_engine.services.persistent_memory import MemoryStore, RETRIEVAL_PROTOCOLS, _specific_sources


class SyntheticEmbeddings:
    def embed(self, text, *, deadline=None):
        return ([1, 0, 0] if any(term in text.lower() for term in ('mountain', 'hiking', 'peaks')) else [0, 1, 0]), 'synthetic-model-v1'


def leave_hot_journal(database, identity):
    code="""import os,sqlite3,sys
db=sqlite3.connect(sys.argv[1])
db.execute('PRAGMA cache_size=1')
db.execute('BEGIN IMMEDIATE')
db.execute('UPDATE memories SET record=zeroblob(65536) WHERE id=?',(sys.argv[2],))
os._exit(86)
"""
    child=subprocess.run([sys.executable,'-c',code,str(database),identity],capture_output=True,timeout=30)
    assert child.returncode==86
    journal=Path(str(database)+'-journal')
    assert journal.is_file() and journal.read_bytes()[:8]!=b'\0'*8


class PersistentMemoryTests(TestCase):
    def setUp(self):
        self.directory = self.enterContext(TemporaryDirectory(prefix='alfred-memory-synthetic-'))
        self.store = MemoryStore(self.directory, embedder=SyntheticEmbeddings())
        self.alice = get_user_model().objects.create_user(username='synthetic-memory-alice')
        self.bob = get_user_model().objects.create_user(username='synthetic-memory-bob')

    def save(self, user=None, **kwargs):
        return self.store.save_verified(user or self.alice, {'preference': 'Quiet mountain travel'},
            {'source': 'synthetic owner confirmation', 'reference': 'synthetic-1'}, verified=True, **kwargs)

    def test_verified_memory_survives_fresh_owner_instance_and_session(self):
        identity = self.save()
        self.client.force_login(self.alice)
        self.client.logout()
        self.client.force_login(get_user_model().objects.get(pk=self.alice.pk))
        fresh = MemoryStore(self.directory, embedder=SyntheticEmbeddings())
        result = fresh.retrieve(get_user_model().objects.get(pk=self.alice.pk), 'hiking near peaks')
        self.assertEqual(result[0]['id'], identity)
        self.assertEqual(result[0]['provenance']['reference'], 'synthetic-1')
        self.assertEqual(result[0]['sensitivity'], 'sensitive')
        self.assertEqual(result[0]['score'], 1)

    def test_abrupt_sqlite_writer_recovers_without_losing_committed_memory_or_key(self):
        from hashlib import sha256
        identity=self.save()
        key_hash=sha256(self.store.key_file.read_bytes()).hexdigest()
        leave_hot_journal(self.store.database,identity)
        recovered=MemoryStore(self.directory,embedder=SyntheticEmbeddings())
        self.assertEqual(recovered.retrieve(self.alice,'mountain')[0]['id'],identity)
        self.assertEqual(recovered.retrieve(self.bob,'mountain'),[])
        self.assertTrue(sha256(recovered.key_file.read_bytes()).hexdigest()==key_hash)
        with closing(sqlite3.connect(recovered.database)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(),[('ok',)])
            for table in ('memories','memory_keys','events'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],1)

    def test_ownership_applies_to_retrieval_and_journal_restore(self):
        alice_id = self.save()
        self.assertEqual(self.store.retrieve(self.bob, 'mountain'), [])
        bob_id = self.save(self.bob)
        self.assertEqual(self.store.restore_owner(self.bob), 1)
        self.assertEqual(self.store.retrieve(self.bob, 'mountain')[0]['id'], bob_id)
        self.assertEqual(self.store.retrieve(self.alice, 'mountain')[0]['id'], alice_id)

    def test_unverified_invalid_and_anonymous_memory_never_calls_embedding(self):
        embedder = Mock()
        store = MemoryStore(self.directory, embedder=embedder)
        for content, provenance, sensitivity, verified in [({}, {'source': 'synthetic'}, 'sensitive', True), ({'x': 1}, {}, 'sensitive', True), ({'x': 1}, {'source': 'synthetic'}, 'unknown', True), ({'x': float('nan')}, {'source': 'synthetic'}, 'sensitive', True), ({'x': 1}, {'source': 'synthetic'}, 'sensitive', False)]:
            with self.assertRaises(ValueError):
                store.save_verified(self.alice, content, provenance, sensitivity=sensitivity, verified=verified)
        with self.assertRaises(PermissionError):
            store.retrieve(AnonymousUser(), 'synthetic')
        embedder.embed.assert_not_called()

    def test_encrypted_events_are_append_only_and_replay_is_idempotent(self):
        identity = self.save()
        with closing(sqlite3.connect(self.store.database)) as db, db:
            ciphertext = db.execute('SELECT ciphertext FROM events').fetchone()[0]
            self.assertNotIn(b'Quiet mountain', ciphertext)
            for sql in ('UPDATE events SET owner="tampered"', 'DELETE FROM events'):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)
            db.execute('DELETE FROM memories')
        restarted = MemoryStore(self.directory, embedder=SyntheticEmbeddings())
        self.assertEqual(restarted.restore_owner(self.alice), 1)
        self.assertEqual(restarted.restore_owner(self.alice), 1)
        self.assertEqual(restarted.retrieve(self.alice, 'mountain')[0]['id'], identity)
        with closing(sqlite3.connect(self.store.database)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 1)

    def test_corrupt_journal_preserves_existing_index(self):
        identity = self.save()
        with closing(sqlite3.connect(self.store.database)) as db:
            before = db.execute('SELECT record FROM memories WHERE id=?', (identity,)).fetchone()[0]
        with closing(sqlite3.connect(self.store.database)) as db, db:
            db.execute('DROP TRIGGER events_no_update')
            db.execute('UPDATE events SET ciphertext=?', (b'synthetic-corrupt-ciphertext',))
        with self.assertRaisesRegex(RuntimeError, 'verification failed'):
            self.store.restore_owner(self.alice)
        with closing(sqlite3.connect(self.store.database)) as db:
            self.assertEqual(db.execute('SELECT record FROM memories WHERE id=?', (identity,)).fetchone()[0], before)

    def test_missing_key_is_never_replaced_when_events_exist(self):
        self.save()
        recovery = self.store.key_file.read_bytes()
        self.store.key_file.unlink()
        with self.assertRaisesRegex(RuntimeError, 'recovery key is missing'):
            self.store.restore_owner(self.alice)
        self.assertFalse(self.store.key_file.exists())
        self.store.key_file.write_bytes(recovery)
        self.assertEqual(self.store.restore_owner(self.alice), 1)

    def test_cloud_reasoning_requires_consent_and_public_classification(self):
        self.save()
        for consent in (False, True):
            with self.assertRaises(PermissionError):
                self.store.retrieve(self.alice, 'mountain', cloud=True, cloud_consent=consent)
        self.save(self.bob, sensitivity='public')
        self.assertEqual(len(self.store.retrieve(self.bob, 'mountain', cloud=True, cloud_consent=True)), 1)

    def test_embedding_failure_commits_no_memory_or_event(self):
        self.store.embedder = Mock()
        self.store.embedder.embed.side_effect = EmbeddingUnavailable('synthetic unavailable')
        with self.assertRaises(EmbeddingUnavailable):
            self.save()
        with closing(sqlite3.connect(self.store.database)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memories').fetchone()[0], 0)

    def test_journal_and_index_commit_atomically_on_storage_failure(self):
        with closing(sqlite3.connect(self.store.database)) as db, db:
            db.execute("CREATE TRIGGER synthetic_fail BEFORE INSERT ON memories BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.save()
        with closing(sqlite3.connect(self.store.database)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)

    def test_concurrent_initial_writes_share_key_and_survive_restart(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            identities = list(pool.map(lambda _: self.save(), range(4)))
        self.assertEqual(len(set(identities)), 1)
        self.assertEqual(MemoryStore(self.directory, embedder=SyntheticEmbeddings()).restore_owner(self.alice), 1)

    def test_deduplication_preserves_different_sources_sensitivity_and_owners(self):
        first=self.save(); self.assertEqual(self.save(),first)
        content={'preference':'Quiet mountain travel'}; source={'source':'synthetic alternate confirmation'}
        other=self.store.save_verified(self.alice,content,source,verified=True)
        public=self.store.save_verified(self.alice,content,source,sensitivity='public',verified=True)
        self.assertNotEqual(other,public); self.assertNotEqual(first,self.save(self.bob))
        self.assertEqual(len(self.store.list_memories(self.alice)),3)

    def test_opt_in_relevance_cutoff_abstains_without_changing_legacy_retrieval(self):
        identity=self.save()
        self.assertEqual(self.store.retrieve(self.alice,'coast')[0]['id'],identity)
        self.assertEqual(self.store.retrieve(self.alice,'coast',min_score=0.45),[])
        self.assertEqual(self.store.retrieve(self.alice,'mountain',min_score=0.45)[0]['id'],identity)
        for value in (True,'0.45',float('nan'),float('inf'),1.1,-1.1):
            with self.assertRaises(ValueError): self.store.retrieve(self.alice,'mountain',min_score=value)

    def test_exact_deduplication_preserves_json_boolean_and_number_types(self):
        first=self.store.save_verified(self.alice,{'checked':True},{'source':'synthetic'},verified=True)
        number=self.store.save_verified(self.alice,{'checked':1},{'source':'synthetic'},verified=True)
        self.assertNotEqual(first,number)
        a=self.store.save_verified(self.alice,{'checked':True},{'source':'synthetic','version':True},verified=True)
        b=self.store.save_verified(self.alice,{'checked':True},{'source':'synthetic','version':1},verified=True)
        self.assertNotEqual(a,b)

    def test_changed_embedding_model_refuses_incompatible_retrieval(self):
        self.save()
        self.store.embedder = Mock()
        self.store.embedder.embed.return_value = ([1, 0, 0], 'synthetic-model-v2')
        with self.assertRaises(EmbeddingUnavailable):
            self.store.retrieve(self.alice, 'synthetic')

    def test_experimental_statement_projection_preserves_canonical_content_and_owner_restore(self):
        calls=[]
        embedder=Mock(); embedder.embed.side_effect=lambda text,**kwargs: (calls.append(text) or [1,0,0],'synthetic-model-v1')
        store=MemoryStore(self.directory,embedder=embedder,retrieval_protocol=RETRIEVAL_PROTOCOLS[1])
        content={'statement':'Fictional blue pottery preference'}
        identity=store.save_verified(self.alice,content,{'source':'Synthetic owner review'},verified=True)
        self.assertEqual(calls[0],content['statement'])
        self.assertEqual(store.list_memories(self.alice)[0]['content'],content)
        self.assertEqual(store.retrieve(self.bob,'pottery',min_score=.45),[])
        self.assertEqual(store.restore_owner(self.alice),1)
        self.assertEqual(store.retrieve(self.alice,'pottery',min_score=.45)[0]['id'],identity)
        with self.assertRaises(EmbeddingUnavailable): self.store.retrieval_profile(self.alice)
        with self.assertRaises(EmbeddingUnavailable): self.store.retrieve(self.alice,'pottery')
        structured={'amount':'42.50','verified':True}
        store.save_verified(self.bob,structured,{'source':'Synthetic structured record'},verified=True)
        self.assertEqual(json.loads(calls[-1]),structured)
        for path in store.directory.iterdir():
            if path.is_file(): self.assertNotIn(b'blue pottery',path.read_bytes())

    def test_new_protocol_never_silently_rewrites_existing_index_or_duplicates(self):
        from apps.ml_engine.services.memory_learning import MemoryLearning
        identity=self.save(); before=self.store.list_memories(self.alice)
        candidate=MemoryStore(self.directory,embedder=SyntheticEmbeddings(),retrieval_protocol=RETRIEVAL_PROTOCOLS[1])
        with patch.object(candidate.embedder,'embed') as embed:
            with self.assertRaises(EmbeddingUnavailable): candidate.retrieve(self.alice,'mountain')
            embed.assert_not_called()
        self.assertEqual(candidate.list_memories(self.alice),before)
        revised=MemoryLearning(candidate).revise(self.alice,[identity],None,verified=True,reembed=True)
        self.assertNotEqual(identity,revised)
        self.assertEqual(candidate.list_memories(self.alice)[0]['content'],before[0]['content'])
        self.assertEqual(candidate.retrieve(self.alice,'mountain')[0]['id'],revised)

    def test_specificity_drops_partial_tail_matches_without_top_one_or_cosine_relabeling(self):
        rows=[dict(id='a',content={'statement':'Fictional Tess enjoys beach walks'},score=.9),
            dict(id='b',content={'statement':'Fictional Tess avoids beach walks'},score=.8),
            dict(id='c',content={'statement':'Fictional Tess enjoys forest walks'},score=.7)]
        result=_specific_sources('Where are beach walks preferred?',rows)
        self.assertEqual([row['id'] for row in result],['a','b'])
        self.assertEqual([row['score'] for row in result],[.9,.8])
        self.assertEqual(_specific_sources('A wholly paraphrased request',rows),rows)
        self.assertEqual(_specific_sources('beach forest',rows),rows)

    def test_specificity_cannot_suppress_live_dense_fallback_with_low_or_deleted_lexical_match(self):
        for removed in (False,True):
            with self.subTest(removed=removed):
                directory=self.enterContext(TemporaryDirectory(prefix='alfred-specificity-synthetic-'))
                embedder=Mock()
                vectors={'Fictional Sal ceramic glazing':[.2,.979795897,0],
                    'Fictional Sal makes durable bowls':[.8,.6,0], 'ceramic glazing':[1,0,0]}
                if removed: vectors['Fictional Sal ceramic glazing']=[.95,.3122498999,0]
                embedder.embed.side_effect=lambda text,**kwargs:(vectors[text],'synthetic-specificity-v1')
                store=MemoryStore(directory,embedder=embedder,retrieval_protocol=RETRIEVAL_PROTOCOLS[1])
                low=store.save_verified(self.alice,{'statement':'Fictional Sal ceramic glazing'},{'source':'Synthetic low match'},verified=True)
                high=store.save_verified(self.alice,{'statement':'Fictional Sal makes durable bowls'},{'source':'Synthetic paraphrase'},verified=True)
                def during_query(text,**kwargs):
                    if removed: store.delete_memory(self.alice,low)
                    return vectors[text],'synthetic-specificity-v1'
                embedder.embed.side_effect=during_query
                result=store.retrieve(self.alice,'ceramic glazing',min_score=.45)
                self.assertEqual([row['id'] for row in result],[high]); self.assertEqual(result[0]['score'],.8)

    def test_verified_content_and_provenance_are_snapshotted_before_embedding(self):
        content = {'preference': 'Quiet mountain travel'}
        provenance = {'source': 'synthetic verified source'}
        def embed(text):
            content['preference'] = 'synthetic later mutation'
            provenance['source'] = 'synthetic later mutation'
            return [1, 0, 0], 'synthetic-model-v1'
        self.store.embedder = Mock()
        self.store.embedder.embed.side_effect = embed
        self.store.save_verified(self.alice, content, provenance, verified=True)
        self.store.embedder = SyntheticEmbeddings()
        result = self.store.retrieve(self.alice, 'mountain')[0]
        self.assertEqual(result['content']['preference'], 'Quiet mountain travel')
        self.assertEqual(result['provenance']['source'], 'synthetic verified source')

    def test_synthetic_restore_harness_refuses_any_additional_records(self):
        from scripts.verify_local_memory_slice import main
        identity = self.save()
        self.save(self.bob)
        (self.store.directory / 'synthetic-proof.json').write_text(json.dumps({'synthetic': True, 'memory_id': identity}))
        with patch('sys.argv', ['proof', '--phase', 'restore', '--proof-dir', self.directory]), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)
        with closing(sqlite3.connect(self.store.database)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memories').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 2)


class LocalEmbeddingBoundaryTests(SimpleTestCase):
    def test_shared_deadline_reaches_model_checks_and_embedding_request(self):
        client=OllamaEmbeddings(); deadline=time.monotonic()+60
        with patch.object(client,'_digest',return_value='a'*64) as digest,patch.object(client,'_request',return_value={'embeddings':[[1,0]]}) as request:
            self.assertEqual(client.embed('synthetic query',deadline=deadline)[0],[1,0])
        self.assertEqual(digest.call_count,2)
        self.assertTrue(all(call.kwargs=={'deadline':deadline} for call in digest.call_args_list))
        self.assertEqual(request.call_args.kwargs,{'deadline':deadline})

    def test_expired_embedding_deadline_never_opens_connection(self):
        with patch('apps.ml_engine.services.local_embeddings.HTTPConnection') as connect,self.assertRaises(EmbeddingUnavailable):
            OllamaEmbeddings().embed('synthetic query',deadline=time.monotonic()-1)
        connect.assert_not_called()

    def test_vectors_reject_empty_zero_nan_infinite_and_malformed_values(self):
        for value in ([], [0, 0], [float('nan')], [float('inf')], [True], ['synthetic'], [1] * 4097):
            with self.assertRaises(EmbeddingUnavailable):
                validate_vector(value)

    def test_local_transport_rejects_redirects_without_sensitive_error(self):
        response = Mock(status=302)
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('apps.ml_engine.services.local_embeddings.HTTPConnection', return_value=connection) as connect, self.assertRaisesRegex(EmbeddingUnavailable, '^Local embedding service is unavailable.$'):
            OllamaEmbeddings()._request('POST', '/api/embed', {'input': 'synthetic-sensitive-input'})
        connect.assert_called_once_with('127.0.0.1', 11434, timeout=30)
        response.read.assert_not_called()
        connection.close.assert_called_once()

    def test_model_change_during_embedding_is_rejected(self):
        client = OllamaEmbeddings()
        with patch.object(client, '_digest', side_effect=['a' * 64, 'b' * 64]), patch.object(client, '_request', return_value={'embeddings': [[1, 0]]}), self.assertRaises(EmbeddingUnavailable):
            client.embed('synthetic query')

    def test_remote_model_metadata_is_rejected_before_embedding(self):
        client = OllamaEmbeddings()
        with patch.object(client, '_request', return_value={'models': [{'name': client.model, 'digest': 'a' * 64, 'remote_host': 'https://synthetic-cloud.invalid'}]}), self.assertRaises(EmbeddingUnavailable):
            client.embed('synthetic private query')
