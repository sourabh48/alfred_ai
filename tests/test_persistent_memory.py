from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from contextlib import redirect_stderr
from io import StringIO
import json
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import sqlite3
import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, SimpleTestCase

from apps.ml_engine.services.local_embeddings import OllamaEmbeddings, EmbeddingUnavailable, validate_vector
from apps.ml_engine.services.persistent_memory import MemoryStore


class SyntheticEmbeddings:
    def embed(self, text, *, deadline=None):
        return ([1, 0, 0] if any(term in text.lower() for term in ('mountain', 'hiking', 'peaks')) else [0, 1, 0]), 'synthetic-model-v1'


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
