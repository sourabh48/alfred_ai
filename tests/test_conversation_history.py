"""Synthetic local history; no provider, plaintext index or verified-fact promotion."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import TestCase, Client, override_settings

from apps.ml_engine.services.conversation_history import ConversationHistory, ConversationConflict, ConversationPermission
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_persistent_memory import SyntheticEmbeddings


@override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True)
class ConversationHistoryTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-history-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'), ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(_offline_fixture_patches())
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=SyntheticEmbeddings()))
        self.alice = get_user_model().objects.create_user(username='history-alice')
        self.bob = get_user_model().objects.create_user(username='history-bob')
        self.store = MemoryStore(settings.ALFRED_MEMORY_DIR)
        self.history = ConversationHistory(self.store)
        self.client.force_login(self.alice)
        self.question = dict(query='SYNTHETIC-PRIVATE-HISTORY-QUERY', scope='general', document_id=None)
        self.result = dict(answer='SYNTHETIC-PRIVATE-HISTORY-ANSWER', provider='ollama', classification='ai_generated_hypothesis',
            financial_authority=False, sources=[{'ref':'canonical-finance', 'classification':'canonical_financial_baseline',
            'url':'/expenses/', 'data':{'balance':'SYNTHETIC-SOURCE-NOT-RETAINED'}}])

    def enable(self, user=None, days=7):
        return self.history.configure(user or self.alice, enabled=True, consent=True, days=days)

    def create(self, user=None):
        user = user or self.alice
        self.enable(user)
        return self.history.create(user, 'SYNTHETIC-PRIVATE-HISTORY-TITLE')

    def turn(self, record, **changes):
        payload = {**self.question, 'conversation_id':record['id'], 'conversation_revision':record['revision'], 'request_id':uuid4().hex}
        return {**payload, **changes}

    def post(self, payload, client=None):
        return (client or self.client).post('/api/ai/personal-insights/', json.dumps(payload), content_type='application/json')

    def test_default_off_operator_gate_explicit_consent_and_strict_retention(self):
        self.assertFalse(self.history.policy(self.alice)['enabled'])
        self.assertIsNone(self.history.policy(self.alice)['retention_days'])
        with self.assertRaises(ConversationPermission): self.history.create(self.alice, 'Unsaved')
        with self.assertRaises(ConversationPermission): self.history.configure(self.alice, enabled=True, days=7)
        with override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False):
            with self.assertRaises(ConversationPermission): self.enable()
        for days in (None, True, 0, 31, '7', 1.5):
            with self.subTest(days=days), self.assertRaises(ValueError): self.enable(days=days)
        self.assertTrue(self.enable()['enabled'])
        self.assertFalse(self.history.policy(self.bob)['enabled'])

    def test_atomic_local_answer_numeric_guard_and_replay_idempotence(self):
        record = self.create(); payload = self.turn(record)
        with patch('apps.ml_engine.api.views.hybrid_answer', return_value=self.result) as model:
            first = self.post(payload); self.assertEqual(first.status_code, 200)
            again = self.post(payload); self.assertEqual(again.status_code, 200)
            self.assertEqual(model.call_count, 1)
        saved = self.history.get(self.alice, record['id'])
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(saved['turns'][0]['query'], self.question['query'])
        self.assertEqual(saved['turns'][0]['classification'], 'ai_generated_hypothesis')
        self.assertNotIn('data', saved['turns'][0]['sources'][0])
        self.assertEqual(again.json()['historical'], True)
        self.assertEqual(self.store.list_memories(self.alice), [])
        with patch('apps.ml_engine.api.views.hybrid_answer') as model:
            mismatch = self.post({**payload, 'query':'Changed request'})
            self.assertEqual(mismatch.status_code, 409); model.assert_not_called()

    def test_ciphertext_files_owner_tamper_and_no_sync_or_embedding(self):
        record = self.create(); identity = record['id']
        generation, _ = self.history.prepare(self.alice, identity, 0, 'a'*32, self.question)
        self.history.append(self.alice, identity, 0, 'a'*32, self.question, self.result, generation)
        with closing(sqlite3.connect(self.store.database)) as db:
            wrapped, ciphertext = db.execute('SELECT wrapped,record FROM conversations').fetchone()
            policy = db.execute('SELECT encrypted FROM conversation_policies').fetchone()[0]
            self.assertIsInstance(ciphertext, bytes); self.assertIsInstance(policy, bytes)
            key = self.store._cipher(db).decrypt(wrapped)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memory_keys').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memory_sync').fetchone()[0], 0)
        for file in self.store.directory.iterdir():
            if file.is_file():
                for private in ('SYNTHETIC-PRIVATE-HISTORY-TITLE', self.question['query'], self.result['answer'], 'SYNTHETIC-SOURCE-NOT-RETAINED'):
                    self.assertNotIn(private.encode(), file.read_bytes())
                self.assertNotIn(key, file.read_bytes())
        self.enable(self.bob)
        with self.store._transaction() as db:
            db.execute('UPDATE conversations SET owner=? WHERE id=?', (_owner(self.bob), identity))
        with self.assertRaises(RuntimeError): self.history.get(self.bob, identity)
        with self.store._transaction() as db:
            db.execute('UPDATE conversations SET owner=?,record=? WHERE id=?', (_owner(self.alice), b'corrupt', identity))
        response = self.client.get('/api/ai/conversations/'+identity+'/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('corrupt', response.content.decode())

    def test_foreign_ids_family_grants_and_missing_sessions_cannot_read_or_write(self):
        from apps.family.models import FamilyAccountLink
        FamilyAccountLink.objects.create(created_by=self.alice, linked_user=self.bob,
            invite_code_hash='f'*64, status='accepted', share_financial_summary=True,
            linked_user_share_financial_summary=True, expires_at=datetime.now(timezone.utc)+timedelta(days=1))
        record = self.create(); self.enable(self.bob)
        other = Client(); other.force_login(self.bob)
        identity = record['id']
        self.assertEqual(other.get('/api/ai/conversations/'+identity+'/').status_code, 404)
        self.assertEqual(other.delete('/api/ai/conversations/'+identity+'/').status_code, 404)
        with patch('apps.ml_engine.api.views.hybrid_answer') as model:
            self.assertEqual(self.post(self.turn(record), other).status_code, 409); model.assert_not_called()
        self.assertEqual(other.get('/api/ai/conversations/').json()['conversations'], [])
        self.client.logout()
        self.assertIn(self.client.get('/api/ai/conversations/'+identity+'/').status_code, (401,403))
        self.client.cookies['sessionid'] = 'invalid-synthetic-session'
        self.assertIn(self.client.get('/api/ai/conversations/').status_code, (401,403))

    def test_csrf_cache_headers_strict_owner_payload_and_clear_confirmation(self):
        self.enable(); guarded = Client(enforce_csrf_checks=True); guarded.force_login(self.alice)
        self.assertEqual(guarded.post('/api/ai/conversations/', {'title':'Synthetic'}).status_code, 403)
        response = guarded.get('/api/ai/conversations/')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.post('/api/ai/conversations/', json.dumps({'title':'Synthetic','owner':self.bob.pk}), content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/api/ai/conversations/clear/', json.dumps({'confirm':False}), content_type='application/json').status_code, 400)

    def test_logout_expiry_revoke_clear_and_delete_during_inference_never_append(self):
        for action in ('logout', 'expiry', 'revoke', 'clear', 'delete', 'operator_off'):
            self.client.force_login(self.alice)
            record = self.create(); payload = self.turn(record)
            def infer(*args, **kwargs):
                if action == 'logout': Session.objects.filter(session_key=self.client.session.session_key).delete()
                if action == 'expiry': Session.objects.filter(session_key=self.client.session.session_key).update(expire_date=datetime.now(timezone.utc)-timedelta(seconds=1))
                if action == 'revoke':
                    self.history.configure(self.alice, enabled=False); self.enable()
                if action == 'clear': self.history.clear(self.alice)
                if action == 'delete': self.history.delete(self.alice, record['id'])
                if action == 'operator_off': settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED = False
                return self.result
            with patch('apps.ml_engine.api.views.hybrid_answer', side_effect=infer):
                response = self.post(payload)
            settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED = True
            self.assertIn(response.status_code, (403,409), action)
            if action in ('logout', 'expiry'):
                self.assertIn(self.client.get('/api/ai/conversations/').status_code, (401,403))
            saved = self.history.get(self.alice, record['id'])
            if saved: self.assertEqual(saved['turns'], [])

    def test_model_errors_storage_failure_revision_and_limits_are_atomic(self):
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        record = self.create(); payload = self.turn(record)
        with patch('apps.ml_engine.api.views.hybrid_answer', side_effect=EmbeddingUnavailable('SYNTHETIC-ERROR-CONTENT')):
            response = self.post(payload)
            self.assertEqual(response.status_code, 503); self.assertNotIn('SYNTHETIC-ERROR-CONTENT', response.content.decode())
        from apps.ml_engine.services.conversation_history import _encoded
        def fail_save(value):
            if value['turns']: raise ValueError('synthetic storage failure')
            return _encoded(value)
        with patch('apps.ml_engine.services.conversation_history._encoded', side_effect=fail_save):
            with patch('apps.ml_engine.api.views.hybrid_answer', return_value=self.result):
                self.assertEqual(self.post(payload).status_code, 400)
        self.assertEqual(self.history.get(self.alice, record['id'])['turns'], [])
        with patch('apps.ml_engine.api.views.hybrid_answer', return_value=self.result):
            self.assertEqual(self.post(payload).status_code, 200)
            self.assertEqual(self.post(self.turn(record)).status_code, 409)
            with patch('apps.ml_engine.services.conversation_history.MAX_TURNS', 1):
                self.assertEqual(self.post(self.turn(record, conversation_revision=1)).status_code, 409)
        with patch('apps.ml_engine.services.conversation_history.MAX_CONVERSATIONS', 1), self.assertRaises(ValueError):
            self.history.create(self.alice, 'More')

    def test_retention_shortening_is_monotonic_and_offline_cleanup_honors_expiry(self):
        start = datetime.now(timezone.utc)
        with patch('apps.ml_engine.services.conversation_history.datetime', wraps=datetime) as clock:
            clock.now.return_value = start
            self.enable(days=30); record = self.history.create(self.alice, 'Expiring')
            self.enable(days=1); self.enable(days=30)
            self.assertEqual(datetime.fromisoformat(self.history.get(self.alice, record['id'])['expires_at']), start+timedelta(days=1))
            clock.now.return_value = start+timedelta(days=2)
            self.store.expire_all()
            self.assertEqual(self.history.list(self.alice), [])
            self.assertEqual(self.store.expire_all(), 0)

    def test_missing_key_never_replaced_and_ciphertext_survives_failed_access(self):
        record = self.create(); protected = self.store.key_file.read_bytes()
        self.store.key_file.unlink()
        with self.assertRaises(RuntimeError): ConversationHistory(MemoryStore(self.store.directory)).get(self.alice, record['id'])
        self.assertFalse(self.store.key_file.exists())
        self.store.key_file.write_bytes(protected)
        self.assertEqual(self.history.get(self.alice, record['id'])['id'], record['id'])

    def test_restart_schema_upgrade_memory_coexistence_and_current_delete_recovery(self):
        from scripts.rehearse_money_migrations import copy_database
        self.store.save_verified(self.alice, {'fact':'Synthetic verified fact'}, {'source':'owner'}, verified=True)
        key = self.store.key_file.read_bytes()
        with self.store._transaction() as db:
            before = db.execute('SELECT * FROM memories').fetchall()
            db.execute('DROP TABLE conversations'); db.execute('DROP TABLE conversation_policies')
        restarted = MemoryStore(self.store.directory)
        with restarted._transaction() as db: self.assertEqual(db.execute('SELECT * FROM memories').fetchall(), before)
        self.assertEqual(restarted.key_file.read_bytes(), key)
        record = self.create()
        code = '''
from django.conf import settings
settings.configure(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True)
from datetime import datetime
from types import SimpleNamespace
from pathlib import Path
import sys
from apps.ml_engine.services.persistent_memory import MemoryStore
from apps.ml_engine.services.conversation_history import ConversationHistory
owner=SimpleNamespace(pk=int(sys.argv[2]),created_at=datetime.fromisoformat(sys.argv[3]),is_authenticated=True)
record=ConversationHistory(MemoryStore(Path(sys.argv[1]),embedder=object())).get(owner,sys.argv[4])
assert record['id']==sys.argv[4]
print('RESTART_PRIVATE_HISTORY_PASS')
'''
        child = subprocess.run([sys.executable, '-B', '-c', code, str(self.store.directory), str(self.alice.pk),
            self.alice.created_at.isoformat(), record['id']], capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0)
        self.assertIn('RESTART_PRIVATE_HISTORY_PASS', child.stdout)
        backup = self.store.directory/'synthetic-old-copy.sqlite3'
        copy_database(self.store.database, backup)
        self.assertTrue(self.history.policy(self.alice)['rollback_requires_clear'])
        self.history.delete(self.alice, record['id'])
        restarted.restore_owner(self.alice)
        self.assertIsNone(ConversationHistory(restarted).get(self.alice, record['id']))
        self.history.configure(self.alice, enabled=False)
        self.assertFalse(self.history.policy(self.alice)['rollback_requires_clear'])
        with closing(sqlite3.connect(backup)) as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0], 1)
        self.assertEqual(len(restarted.list_memories(self.alice)), 1)
        baseline = subprocess.run(['git', 'show', 'bdabc389764119d95e2a002946b8fa8088c1bc6b:apps/ml_engine/services/persistent_memory.py'],
            capture_output=True, text=True, encoding='utf-8', timeout=30, check=True).stdout
        code = '''
from django.conf import settings
settings.configure()
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
baseline=ModuleType('apps.ml_engine.services.rollback_baseline')
baseline.__package__='apps.ml_engine.services'
exec(sys.stdin.read(),baseline.__dict__)
owner=SimpleNamespace(pk=int(sys.argv[2]),created_at=datetime.fromisoformat(sys.argv[3]),is_authenticated=True)
store=baseline.MemoryStore(Path(sys.argv[1]),embedder=object())
assert len(store.list_memories(owner))==1
with store._transaction() as db:
    assert db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]==0
print('BASELINE_VAULT_ROLLBACK_PASS')
'''
        rollback = subprocess.run([sys.executable, '-B', '-c', code, str(self.store.directory), str(self.alice.pk),
            self.alice.created_at.isoformat()], input=baseline, capture_output=True, text=True, timeout=30)
        self.assertEqual(rollback.returncode, 0)
        self.assertIn('BASELINE_VAULT_ROLLBACK_PASS', rollback.stdout)

    def test_account_reset_and_delete_revoke_history_without_touching_other_owner(self):
        from apps.users.services import clear_user_fed_data
        alice = self.create(); bob = self.create(self.bob)
        clear_user_fed_data(self.alice)
        self.assertFalse(self.history.policy(self.alice)['enabled'])
        self.assertEqual(self.history.get(self.bob, bob['id'])['id'], bob['id'])
        self.alice.delete()
        self.bob.delete()
        with self.store._transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0], 0)

    def test_history_never_calls_cloud_and_fresh_financial_guard_is_unchanged(self):
        from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
        record = self.create()
        with patch('apps.ml_engine.services.memory_reasoning.reasoning_provider', side_effect=AssertionError('No cloud')):
            self.assertEqual(self.post(self.turn(record, cloud_consent=True)).status_code, 403)
        local = Mock(); local.reason.return_value = 'Your balance is USD 999.'
        result = hybrid_answer(self.store, self.alice, 'Explain current finances', scope='finance', local=local)
        self.assertTrue(result['narrative_withheld']); self.assertFalse(result['financial_authority'])
        self.assertIsNone(result['sources'][0]['data']['amounts']['monthly_income']['currency'])
        self.assertNotIn('history', local.reason.call_args.args[0])

    def test_history_lifecycle_preserves_financial_rows_and_canonical_decimal_baseline(self):
        from apps.expenses.models import BankAccount, Expense
        from apps.loans.models import Loan
        from apps.investments.models import Investment
        from apps.family.models import FamilyAccountLink
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        from tests.user_acceptance_scenario import seed_acceptance_user
        self.client.logout()
        self.alice = seed_acceptance_user(self.client)['user']
        self.client.force_login(self.alice)
        models = (get_user_model(), BankAccount, Expense, Loan, Investment, FamilyAccountLink)
        snapshot = lambda: [list(model.objects.order_by('pk').values()) for model in models]
        before = snapshot()
        baseline = resolve_canonical_financial_baseline(self.alice)['decimal_amounts']
        record = self.create()
        with patch('apps.ml_engine.api.views.hybrid_answer', return_value=self.result):
            self.assertEqual(self.post(self.turn(record, scope='finance')).status_code, 200)
        self.history.clear(self.alice)
        self.history.configure(self.alice, enabled=False)
        self.assertEqual(snapshot(), before)
        self.assertEqual(resolve_canonical_financial_baseline(self.alice)['decimal_amounts'], baseline)

    def test_failed_history_save_retains_only_redacted_error_class_and_reference(self):
        record = self.create()
        with patch('apps.ml_engine.api.views.hybrid_answer', side_effect=RuntimeError(self.question['query'])):
            with self.assertLogs('apps.ml_engine.api.memory', level='ERROR') as captured:
                response = self.post(self.turn(record))
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json()['error_id'])
        self.assertIn(response.json()['error_id'], captured.output[0])
        self.assertIn('RuntimeError', captured.output[0])
        for value in (self.question['query'], self.result['answer'], 'SYNTHETIC-PRIVATE-HISTORY-TITLE'):
            self.assertNotIn(value, response.content.decode())
            self.assertNotIn(value, ''.join(captured.output))
        self.assertEqual(self.history.get(self.alice, record['id'])['turns'], [])
