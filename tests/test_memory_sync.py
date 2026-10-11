from contextlib import closing
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from cryptography.fernet import Fernet

from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider, SyncConflict, SyncUnavailable, encoded
from tests.test_persistent_memory import SyntheticEmbeddings

class MemorySyncTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-sync-synthetic-')))
        self.alice=get_user_model().objects.create_user(username='synthetic-sync-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-sync-bob')
        self.store=MemoryStore(self.root/'alice-one',embedder=SyntheticEmbeddings())
        self.provider=MockCloudProvider(self.root/'mock-provider')
        self.sync=MemorySynchronizer(self.store,self.provider)
        self.sync.configure(self.alice,enabled=True,consent=True)

    def save(self,store=None,user=None):
        return (store or self.store).save_verified(user or self.alice,{'preference':'SYNTHETIC-PRIVATE-OCR mountain holiday'},
            {'source':'SYNTHETIC-ACCOUNT-9001'},verified=True)

    def second(self):
        store=MemoryStore(self.root/'alice-two',embedder=SyntheticEmbeddings())
        key='sync-'+_owner(self.alice)+'.key'
        (store.directory/key).write_bytes((self.store.directory/key).read_bytes())
        sync=MemorySynchronizer(store,self.provider)
        sync.configure(self.alice,enabled=True,consent=True)
        return store,sync

    def retry_now(self,sync):
        with sync.store._transaction() as db:
            state=sync.store._sync_state(db,_owner(self.alice)); state['retry_at']=0
            sync.store._write_sync_state(db,_owner(self.alice),state)

    def test_save_upload_restart_download_retrieve(self):
        identity=self.save(); self.assertEqual(self.sync.run(self.alice),'uploaded')
        other,sync=self.second()
        self.assertEqual(sync.run(self.alice),'downloaded')
        self.assertEqual(other.retrieve(self.alice,'mountain')[0]['id'],identity)
        self.assertEqual(other.restore_owner(self.alice),1)
        self.assertEqual(other.retrieve(self.bob,'mountain'),[])

    def test_cloud_objects_and_local_queue_contain_no_plaintext_or_raw_record_keys(self):
        identity=self.save(); self.provider.offline=True
        with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        self.assertTrue(self.sync.status(self.alice)['pending'])
        self.provider.offline=False; self.retry_now(self.sync); self.sync.run(self.alice)
        with self.store._transaction() as db:
            key=self.store._cipher(db).decrypt(db.execute('SELECT wrapped FROM memory_keys WHERE id=?',(identity,)).fetchone()[0])
        for path in self.root.rglob('*'):
            if path.is_file():
                for secret in (b'SYNTHETIC-PRIVATE-OCR',b'SYNTHETIC-ACCOUNT-9001',key): self.assertNotIn(secret,path.read_bytes())

    def test_disabled_or_missing_consent_never_contacts_provider(self):
        with self.assertRaises(PermissionError): self.sync.configure(self.bob,enabled=True)
        with self.assertRaises(PermissionError): self.sync.status(AnonymousUser())
        self.sync.configure(self.alice,enabled=False)
        with patch.object(self.provider,'head',side_effect=AssertionError('No cloud')):
            self.assertEqual(self.sync.run(self.alice),'disabled')

    def test_offline_retry_survives_restart_and_backoff(self):
        self.save(); self.provider.offline=True
        with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        restarted=MemorySynchronizer(MemoryStore(self.store.directory,embedder=SyntheticEmbeddings()),self.provider)
        self.assertEqual(restarted.run(self.alice),'queued')
        self.provider.offline=False; self.retry_now(restarted)
        self.assertEqual(restarted.run(self.alice),'uploaded')
        self.assertFalse(restarted.status(self.alice)['pending'])

    def test_immutable_versions_and_mutable_current_manifest(self):
        identity=self.save(); self.sync.run(self.alice)
        self.store.delete_memory(self.alice,identity); self.sync.run(self.alice)
        with closing(sqlite3.connect(self.provider.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM objects').fetchone()[0],2)
            with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE objects SET ciphertext=X'00'")
        head=self.provider.head(_owner(self.alice),deadline=time.monotonic()+5)
        manifest=json.loads(self.sync._key(_owner(self.alice)).decrypt(head['manifest']))
        self.assertEqual(manifest['keys'],{})

    def test_revoked_memory_removed_after_remote_download_and_old_head_refused(self):
        identity=self.save(); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        old=self.provider.head(_owner(self.alice),deadline=time.monotonic()+5)
        self.store.delete_memory(self.alice,identity); self.sync.run(self.alice)
        self.assertEqual(sync.run(self.alice),'downloaded'); self.assertEqual(other.list_memories(self.alice),[])
        with patch.object(self.provider,'head',return_value=old),self.assertRaises(SyncConflict): sync.run(self.alice)
        self.assertEqual(other.restore_owner(self.alice),0)

    def test_conflict_preserves_local_edits_and_explicit_merge_recovers(self):
        self.save(); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        first=self.save(); second=self.save(other)
        self.sync.run(self.alice)
        with self.assertRaises(SyncConflict): sync.run(self.alice)
        self.assertIn(second,{r['id'] for r in other.list_memories(self.alice)})
        self.assertTrue(sync.status(self.alice)['conflict'])
        self.assertEqual(sync.run(self.alice,recover=True),'uploaded')
        self.assertIn(first,{r['id'] for r in other.list_memories(self.alice)})
        self.sync.run(self.alice)
        self.assertIn(second,{r['id'] for r in self.store.list_memories(self.alice)})

    def test_conflict_applies_remote_revocation_before_recovery(self):
        identity=self.save(); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        new=self.save(other); self.store.delete_memory(self.alice,identity); self.sync.run(self.alice)
        with self.assertRaises(SyncConflict): sync.run(self.alice)
        self.assertEqual({r['id'] for r in other.list_memories(self.alice)},{new})
        sync.run(self.alice,recover=True)
        self.assertEqual({r['id'] for r in other.list_memories(self.alice)},{new})

    def test_reset_wins_over_offline_old_generation_and_preserves_bob(self):
        self.save(); bob=self.save(user=self.bob); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        self.save(other); self.store.reset_owner(self.alice); self.sync.run(self.alice)
        with self.assertRaises(SyncConflict): sync.run(self.alice)
        self.assertEqual(other.list_memories(self.alice),[])
        sync.run(self.alice,recover=True)
        self.assertEqual(self.store.list_memories(self.bob)[0]['id'],bob)

    def test_tampering_preserves_current_index_and_safe_error(self):
        identity=self.save(); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        self.save(); self.sync.run(self.alice)
        head=self.provider.head(_owner(self.alice),deadline=time.monotonic()+5); head['manifest']=b'SYNTHETIC-PRIVATE-OCR'
        with patch.object(self.provider,'head',return_value=head),self.assertRaisesRegex(SyncUnavailable,'^Memory synchronization is unavailable; encrypted local updates remain queued.$'):
            sync.run(self.alice)
        self.assertEqual(other.retrieve(self.alice,'mountain')[0]['id'],identity)

    def test_missing_key_is_not_regenerated(self):
        self.save(); self.sync.run(self.alice)
        path=self.store.directory/('sync-'+_owner(self.alice)+'.key'); original=path.read_bytes(); path.unlink()
        with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        self.assertFalse(path.exists()); path.write_bytes(original)

    def test_concurrent_remote_cas_rejects_overwrite(self):
        self.save(); self.sync.run(self.alice)
        head=self.provider.head(_owner(self.alice),deadline=time.monotonic()+5)
        with self.assertRaises(SyncConflict):
            self.provider.publish(_owner(self.alice),0,head['identity'],self.provider.download(_owner(self.alice),head['identity'],deadline=time.monotonic()+5),head['manifest'],deadline=time.monotonic()+5)

    def test_local_delete_during_upload_stays_queued(self):
        identity=self.save()
        publish=self.provider.publish
        def racing(*args,**kwargs):
            self.store.delete_memory(self.alice,identity)
            return publish(*args,**kwargs)
        with patch.object(self.provider,'publish',side_effect=racing): self.sync.run(self.alice)
        self.assertTrue(self.sync.status(self.alice)['pending'])
        self.assertEqual(self.store.list_memories(self.alice),[])
        self.sync.run(self.alice)
        head=self.provider.head(_owner(self.alice),deadline=time.monotonic()+5)
        self.assertEqual(json.loads(self.sync._key(_owner(self.alice)).decrypt(head['manifest']))['keys'],{})

    def test_lost_publish_response_acknowledges_existing_version(self):
        self.save(); publish=self.provider.publish
        def lost(*args,**kwargs):
            publish(*args,**kwargs)
            raise OSError('synthetic secret response lost')
        with patch.object(self.provider,'publish',side_effect=lost),self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        self.retry_now(self.sync)
        self.assertEqual(self.sync.run(self.alice),'current')
        with closing(sqlite3.connect(self.provider.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM objects').fetchone()[0],1)
        self.assertFalse(self.sync.status(self.alice)['pending'])

    def test_retention_expires_downloaded_record_and_queues_key_revocation(self):
        with patch('apps.ml_engine.services.persistent_memory.datetime') as clock:
            clock.now.return_value=datetime.now(timezone.utc)-timedelta(days=31)
            self.save()
        self.store.set_retention(self.alice,365); self.sync.run(self.alice)
        # The authenticated remote policy is shortened without changing immutable content.
        owner=_owner(self.alice); head=self.provider.head(owner,deadline=time.monotonic()+5)
        cipher=self.sync._key(owner)
        body=json.loads(cipher.decrypt(self.provider.download(owner,head['identity'],deadline=time.monotonic()+5)))
        body.update(retention=1,revision=2,parent=head['identity'])
        ciphertext=cipher.encrypt(encoded(body)); identity=sha256(ciphertext).hexdigest()
        manifest=json.loads(cipher.decrypt(head['manifest'])); manifest.update(revision=2,identity=identity)
        self.provider.publish(owner,1,identity,ciphertext,cipher.encrypt(encoded(manifest)),deadline=time.monotonic()+5)
        other,sync=self.second(); self.assertEqual(sync.run(self.alice),'downloaded')
        self.assertEqual(other.list_memories(self.alice),[])
        self.assertTrue(sync.status(self.alice)['pending'])
        sync.run(self.alice)
        head=self.provider.head(owner,deadline=time.monotonic()+5)
        self.assertEqual(json.loads(cipher.decrypt(head['manifest']))['keys'],{})

    def test_explicit_merge_expiry_queues_remote_key_revocation(self):
        with patch('apps.ml_engine.services.persistent_memory.datetime') as clock:
            clock.now.return_value=datetime.now(timezone.utc)-timedelta(days=31)
            self.save()
        self.store.set_retention(self.alice,365); self.sync.run(self.alice)
        other,sync=self.second(); sync.run(self.alice)
        other.set_retention(self.alice,1)
        with patch('apps.ml_engine.services.persistent_memory.datetime') as clock:
            clock.now.return_value=datetime.now(timezone.utc)-timedelta(days=10)
            clock.fromisoformat=datetime.fromisoformat
            self.save()
        self.save(); self.sync.run(self.alice)
        # The remote policy is longer; recovery takes the shorter local policy,
        # then expiry changes the merged snapshot after publishing it.
        self.assertEqual(sync.run(self.alice,recover=True),'uploaded')
        self.assertTrue(sync.status(self.alice)['pending'])
        self.assertEqual(len(other.list_memories(self.alice)),1)
        self.assertEqual(sync.run(self.alice),'uploaded')
        owner=_owner(self.alice); head=self.provider.head(owner,deadline=time.monotonic()+5)
        manifest=json.loads(sync._key(owner).decrypt(head['manifest']))
        self.assertEqual(len(manifest['keys']),1)

    def test_missing_master_key_with_only_sync_metadata_is_never_replaced(self):
        original=self.store.key_file.read_bytes(); self.store.key_file.unlink()
        with self.assertRaises(RuntimeError): self.sync.status(self.alice)
        self.assertFalse(self.store.key_file.exists()); self.store.key_file.write_bytes(original)

    def test_authenticated_history_fork_preserves_index(self):
        identity=self.save(); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        self.save(); self.sync.run(self.alice)
        owner=_owner(self.alice); head=self.provider.head(owner,deadline=time.monotonic()+5)
        cipher=self.sync._key(owner)
        body=json.loads(cipher.decrypt(self.provider.download(owner,head['identity'],deadline=time.monotonic()+5)))
        body['parent']='f'*64; ciphertext=cipher.encrypt(encoded(body)); head['identity']=sha256(ciphertext).hexdigest()
        manifest=json.loads(cipher.decrypt(head['manifest'])); manifest['identity']=head['identity']; head['manifest']=cipher.encrypt(encoded(manifest))
        with patch.object(self.provider,'head',return_value=head),patch.object(self.provider,'download',return_value=ciphertext),self.assertRaises(SyncConflict): sync.run(self.alice)
        self.assertEqual(other.retrieve(self.alice,'mountain')[0]['id'],identity)

    def test_download_preserves_concurrent_encrypted_budget_updates(self):
        self.save(); self.sync.run(self.alice); other,sync=self.second()
        head=self.provider.head
        def budget(*args,**kwargs):
            with other._transaction() as db:
                state=other._sync_state(db,_owner(self.alice)); state['reasoning']={'day':'2026-10-11','reserved':1000}
                other._write_sync_state(db,_owner(self.alice),state)
            return head(*args,**kwargs)
        with patch.object(self.provider,'head',side_effect=budget): self.assertEqual(sync.run(self.alice),'downloaded')
        with other._transaction() as db: self.assertEqual(other._sync_state(db,_owner(self.alice))['reasoning']['reserved'],1000)

    def test_consent_revocation_during_download_prevents_import(self):
        self.save(); self.sync.run(self.alice); other,sync=self.second(); head=self.provider.head
        def revoked(*args,**kwargs):
            sync.configure(self.alice,enabled=False)
            return head(*args,**kwargs)
        with patch.object(self.provider,'head',side_effect=revoked),self.assertRaises(SyncConflict): sync.run(self.alice)
        self.assertEqual(other.list_memories(self.alice),[]); self.assertFalse(sync.status(self.alice)['enabled'])

    def test_deadline_and_download_size_checked_before_payload_allocation(self):
        with self.assertRaises(SyncUnavailable): self.provider.head(_owner(self.alice),deadline=time.monotonic()-1)
        identity=self.save(); self.sync.run(self.alice)
        head=self.provider.head(_owner(self.alice),deadline=time.monotonic()+5)
        with self.assertRaises(SyncUnavailable): self.provider.download(_owner(self.alice),head['identity'],deadline=time.monotonic()+5,maximum=1)
        for seconds in (0,-1,6,True,float('nan')):
            with self.assertRaises(ValueError): self.sync.run(self.alice,seconds=seconds)
