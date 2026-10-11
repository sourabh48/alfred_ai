"""Synthetic encrypted storage, deletion/recovery, session/CSRF and retention proofs."""
from contextlib import closing
from datetime import datetime, timezone, timedelta
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock

from cryptography.fernet import Fernet, InvalidToken
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, Client

from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from apps.ml_engine.services.memory_key import MemoryStorageUnavailable, protect_key
from tests.test_persistent_memory import SyntheticEmbeddings


class MemoryPrivacyTests(TestCase):
    def setUp(self):
        self.directory = self.enterContext(TemporaryDirectory(prefix='alfred-private-memory-synthetic-'))
        from django.test import override_settings
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=self.directory,
            ALFRED_ABUSE_THROTTLE_DIR=str(Path(self.directory) / 'limits')))
        self.alice = get_user_model().objects.create_user(username='synthetic-private-memory-alice')
        self.bob = get_user_model().objects.create_user(username='synthetic-private-memory-bob')
        self.embedder = SyntheticEmbeddings()
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=self.embedder))
        self.store = MemoryStore(self.directory)

    def save(self, user=None, **kw):
        return self.store.save_verified(user or self.alice, {'secret': 'SYNTHETIC-PRIVATE-OCR-9001'},
            {'source': 'SYNTHETIC-PROVENANCE-ACCOUNT-1000'}, verified=True, **kw)

    def test_index_journal_keys_and_files_contain_no_plaintext(self):
        identity = self.save()
        with closing(sqlite3.connect(self.store.database)) as db:
            row = db.execute('SELECT id,owner,record FROM memories').fetchone()
            self.assertIsInstance(row[2], bytes)
            self.assertEqual(self.store._decode(db, *row)['id'], identity)
            wrapped = db.execute('SELECT wrapped FROM memory_keys').fetchone()[0]
            master = self.store._cipher(db)
            key = master.decrypt(wrapped)
        for file in Path(self.directory).iterdir():
            if file.is_file():
                payload = file.read_bytes()
                for secret in (b'SYNTHETIC-PRIVATE-OCR-9001', b'SYNTHETIC-PROVENANCE-ACCOUNT-1000', key):
                    self.assertNotIn(secret, payload)
        self.assertTrue(self.store.key_file.read_bytes().startswith(b'M15DPAPI1\0'))
        self.assertFalse(Path(str(self.store.database) + '-wal').exists())
        self.assertFalse(Path(str(self.store.database) + '-journal').exists())
        with self.assertRaises(MemoryStorageUnavailable):
            protect_key(b'invalid-synthetic-dpapi', decrypt=True)

    def test_delete_revokes_key_and_never_returns_during_restore(self):
        identity = self.save()
        bob_id = self.save(self.bob)
        self.assertEqual(self.store.delete_memory(self.bob, identity), 0)
        self.assertEqual(self.store.delete_memory(self.alice, identity), 1)
        self.assertEqual(self.store.delete_memory(self.alice, identity), 0)
        restarted = MemoryStore(self.directory)
        self.assertEqual(restarted.restore_owner(self.alice), 0)
        self.assertEqual(restarted.list_memories(self.alice), [])
        self.assertEqual(restarted.list_memories(self.bob)[0]['id'], bob_id)
        with closing(sqlite3.connect(self.store.database)) as db:
            self.assertIsNone(db.execute('SELECT wrapped FROM memory_keys WHERE id=?', (identity,)).fetchone())
            ciphertext = db.execute('SELECT ciphertext FROM events WHERE id=?', (identity,)).fetchone()[0]
            with self.assertRaises(InvalidToken):
                restarted._cipher(db).decrypt(ciphertext)

    def test_reset_repeated_and_offline_restart_preserves_other_owner(self):
        self.save()
        self.save()
        bob_id = self.save(self.bob)
        self.assertEqual(self.store.reset_owner(self.alice), 2)
        self.assertEqual(self.store.reset_owner(self.alice), 0)
        with patch('apps.ml_engine.services.local_embeddings.HTTPConnection', side_effect=AssertionError('No network for recovery')):
            restarted = MemoryStore(self.directory)
            self.assertEqual(restarted.restore_owner(self.alice), 0)
            self.assertEqual(restarted.restore_owner(self.bob), 1)
            self.assertEqual(restarted.list_memories(self.bob)[0]['id'], bob_id)

    def test_user_retention_revokes_expired_events_even_with_missing_index(self):
        old = datetime.now(timezone.utc) - timedelta(days=40)
        with patch('apps.ml_engine.services.persistent_memory.datetime') as clock:
            clock.now.return_value = old
            clock.fromisoformat = datetime.fromisoformat
            identity = self.save()
            self.store.set_retention(self.bob, 90)
            bob_id = self.save(self.bob)
        with closing(sqlite3.connect(self.store.database)) as db, db:
            db.execute('DELETE FROM memories WHERE id=?', (identity,))
        out = StringIO()
        call_command('prune_private_memory', stdout=out)
        self.assertIn('revoked: 1', out.getvalue())
        self.assertEqual(self.store.restore_owner(self.alice), 0)
        self.assertEqual(self.store.restore_owner(self.bob), 1)
        self.assertEqual(self.store.list_memories(self.bob)[0]['id'], bob_id)
        self.assertEqual(self.store.expire_all(), 0)

    def test_shortening_retention_expires_now_and_invalid_policy_is_atomic(self):
        old = datetime.now(timezone.utc) - timedelta(days=10)
        with patch('apps.ml_engine.services.persistent_memory.datetime') as clock:
            clock.now.return_value = old
            self.save()
        self.assertEqual(self.store.set_retention(self.alice, 1), 1)
        for value in (0, 366, True, '30', None):
            with self.assertRaises(ValueError):
                self.store.set_retention(self.alice, value)
        self.assertEqual(self.store.retention_days(self.alice), 1)
        self.assertEqual(self.store.restore_owner(self.alice), 0)

    def test_revocation_during_retrieval_discards_old_context(self):
        self.save()
        embedder = Mock()
        def embed(query):
            self.store.reset_owner(self.alice)
            return [0, 1, 0], 'synthetic-model-v1'
        embedder.embed.side_effect = embed
        self.store.embedder = embedder
        self.assertEqual(self.store.retrieve(self.alice, 'synthetic'), [])

    def test_reset_during_embedding_refuses_late_save(self):
        embedder = Mock()
        def embed(query):
            self.store.reset_owner(self.alice)
            return [0, 1, 0], 'synthetic-model-v1'
        embedder.embed.side_effect = embed
        self.store.embedder = embedder
        with self.assertRaises(ValueError):
            self.save()
        self.assertEqual(self.store.list_memories(self.alice), [])

    def test_legacy_plaintext_vault_is_preserved_and_refused(self):
        with TemporaryDirectory(prefix='alfred-legacy-memory-synthetic-') as root:
            database = Path(root) / 'verified.sqlite3'
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('CREATE TABLE memories(id TEXT,owner TEXT,record TEXT)')
                db.execute('INSERT INTO memories VALUES(?,?,?)', ('synthetic', 'synthetic', 'SYNTHETIC-LEGACY-PRIVATE'))
            original = database.read_bytes()
            with self.assertRaises(MemoryStorageUnavailable):
                MemoryStore(root)
            self.assertEqual(database.read_bytes(), original)

    def test_family_financial_permission_never_grants_memory_access(self):
        from apps.family.models import FamilyAccountLink
        from django.utils import timezone as django_timezone
        FamilyAccountLink.objects.create(created_by=self.alice, linked_user=self.bob, status='accepted',
            invite_code_hash='a'*64, invite_code_hint='TEST', expires_at=django_timezone.now()+timedelta(days=1),
            share_financial_summary=True, linked_user_share_financial_summary=True)
        identity = self.save()
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get('/api/ai/memories/').json()['memories'], [])
        self.assertEqual(self.client.delete(f'/api/ai/memories/{identity}/').status_code, 404)
        self.assertEqual(self.store.list_memories(self.alice)[0]['id'], identity)

    def test_session_api_owner_no_store_reset_confirmation_and_untrusted_owner(self):
        self.assertEqual(self.client.get('/api/ai/memories/').status_code, 403)
        self.client.force_login(self.alice)
        payload = {'content': {'x': 'synthetic'}, 'provenance': {'source': 'synthetic'}, 'verified': True}
        self.assertEqual(self.client.post('/api/ai/memories/', payload | {'owner': self.bob.pk}, content_type='application/json').status_code, 400)
        response = self.client.post('/api/ai/memories/', payload, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.post('/api/ai/memories/reset/', {}, content_type='application/json').status_code, 400)
        self.assertEqual(len(self.store.list_memories(self.alice)), 1)
        self.assertEqual(self.client.put('/api/ai/memories/retention/', {'days': 7}, content_type='application/json').status_code, 200)
        self.assertEqual(self.client.post('/api/ai/memories/reset/', {'confirm': True}, content_type='application/json').json()['deleted'], 1)
        self.assertEqual(self.client.post('/api/ai/memories/restore/', {}, content_type='application/json').json()['restored'], 0)

    def test_memory_writes_require_session_csrf_and_ignore_token_header(self):
        identity = self.save()
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.delete(f'/api/ai/memories/{identity}/', HTTP_AUTHORIZATION='Token synthetic').status_code, 403)
        client.force_login(self.alice)
        self.assertEqual(client.delete(f'/api/ai/memories/{identity}/').status_code, 403)
        client.get('/settings/')
        csrf = client.cookies['csrftoken'].value
        self.assertEqual(client.delete(f'/api/ai/memories/{identity}/', HTTP_X_CSRFTOKEN=csrf).status_code, 204)

    def test_memory_api_retrieval_is_local_and_requires_explicit_verification(self):
        identity = self.save()
        self.client.force_login(self.alice)
        response = self.client.post('/api/ai/memories/retrieve/', {'query': 'synthetic'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['memories'][0]['id'], identity)
        self.assertEqual(self.client.post('/api/ai/memories/retrieve/', {'query': 'synthetic', 'cloud': True}, content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/api/ai/memories/', {'content': {'x': 'synthetic'}, 'provenance': {'source': 'synthetic'}}, content_type='application/json').status_code, 400)
        self.assertEqual(len(self.store.list_memories(self.alice)), 1)

    def test_expensive_memory_rate_limit_rejects_before_mutation_per_owner(self):
        from django.test import override_settings
        payload = {'content': {'x': 'synthetic'}, 'provenance': {'source': 'synthetic'}, 'verified': True}
        with override_settings(ALFRED_EXPENSIVE_ACCOUNT_LIMIT=1):
            self.client.force_login(self.alice)
            self.assertEqual(self.client.post('/api/ai/memories/', payload, content_type='application/json').status_code, 201)
            rejected = self.client.post('/api/ai/memories/', payload, content_type='application/json')
            self.assertEqual(rejected.status_code, 429)
            self.assertIn('Retry-After', rejected)
            self.assertEqual(len(self.store.list_memories(self.alice)), 1)
            self.client.force_login(self.bob)
            self.assertEqual(self.client.post('/api/ai/memories/', payload, content_type='application/json').status_code, 201)

    def test_storage_failure_api_and_logging_do_not_disclose_memory(self):
        self.client.force_login(self.alice)
        with patch('apps.ml_engine.api.memory.memory_store', side_effect=OSError('F:/private/SYNTHETIC-PRIVATE-OCR-9001')), self.assertLogs('apps.ml_engine.api.memory', level='ERROR') as logs:
            response = self.client.get('/api/ai/memories/')
        self.assertEqual(response.status_code, 503)
        self.assertIn(response.json()['error_id'], ''.join(logs.output))
        self.assertIn('OSError', ''.join(logs.output))
        self.assertNotIn('SYNTHETIC-PRIVATE-OCR-9001', str(response.content) + ''.join(logs.output))

    def test_account_data_reset_and_account_deletion_revoke_recovery(self):
        self.save()
        self.save(self.bob)
        self.client.force_login(self.alice)
        response = self.client.post('/api/users/profile/clear-data/', {}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['deleted']['private_memories'], 1)
        self.assertEqual(self.store.restore_owner(self.alice), 0)
        self.assertEqual(len(self.store.list_memories(self.bob)), 1)
        owner = self.bob
        identity = owner.pk
        owner.delete()
        owner.pk = identity
        self.assertEqual(self.store.restore_owner(owner), 0)

    def test_memory_reset_failure_blocks_account_financial_mutation(self):
        self.save()
        self.alice.monthly_income = 123
        self.alice.save()
        self.client.force_login(self.alice)
        with patch.object(MemoryStore, 'reset_owner', side_effect=RuntimeError('synthetic-private-error')):
            response = self.client.post('/api/users/profile/clear-data/', {}, content_type='application/json')
        self.assertEqual(response.status_code, 503)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.monthly_income, 123)
        self.assertEqual(len(self.store.list_memories(self.alice)), 1)
