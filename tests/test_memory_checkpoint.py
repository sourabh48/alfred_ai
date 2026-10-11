from contextlib import closing
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider, SyncConflict, SyncUnavailable, encoded
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from tests.test_persistent_memory import SyntheticEmbeddings


class MemoryCheckpointTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-checkpoint-synthetic-')))
        self.alice=get_user_model().objects.create_user(username='synthetic-checkpoint-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-checkpoint-bob')
        self.store=MemoryStore(self.root/'first',embedder=SyntheticEmbeddings())
        self.provider=MockCloudProvider(self.root/'mock')
        self.sync=MemorySynchronizer(self.store,self.provider)
        self.sync.configure(self.alice,enabled=True,consent=True)
        self.identity=self.store.save_verified(self.alice,{'preference':'SYNTHETIC-PRIVATE-CHECKPOINT'},
            {'source':'synthetic owner confirmation'},verified=True)
        self.sync.run(self.alice)
        self.first_head=self.provider.head(_owner(self.alice),deadline=time.monotonic()+5)

    def fresh(self):
        store=MemoryStore(self.root/'fresh',embedder=SyntheticEmbeddings())
        filename='sync-'+_owner(self.alice)+'.key'
        (store.directory/filename).write_bytes((self.store.directory/filename).read_bytes())
        return store,MemorySynchronizer(store,self.provider)

    def test_uncheckpointed_fresh_device_cannot_restore_replayed_deleted_memory(self):
        self.store.delete_memory(self.alice,self.identity); self.sync.run(self.alice)
        store,sync=self.fresh(); sync.configure(self.alice,enabled=True,consent=True)
        with patch.object(self.provider,'head',return_value=self.first_head),self.assertRaises(SyncConflict):
            sync.run(self.alice,recover=True)
        self.assertEqual(store.list_memories(self.alice),[])

    def test_checkpoint_bootstrap_is_password_free_owner_scoped_and_survives_restart(self):
        checkpoint=self.sync.export_checkpoint(self.alice,confirm=True)
        key=self.store.directory/('sync-'+_owner(self.alice)+'.key')
        self.assertNotIn(b'SYNTHETIC-PRIVATE-CHECKPOINT',checkpoint)
        self.assertNotIn(key.read_bytes(),checkpoint)
        payload=json.loads(self.sync._key(_owner(self.alice)).decrypt(checkpoint))
        self.assertEqual(set(payload),{'schema','owner','revision','identity'})
        store,sync=self.fresh(); sync.import_checkpoint(self.alice,checkpoint,confirm=True)
        self.assertFalse(sync.status(self.alice)['enabled'])
        self.assertEqual(sync.run(self.alice),'disabled')
        sync.configure(self.alice,enabled=True,consent=True)
        restarted=MemorySynchronizer(MemoryStore(store.directory,embedder=SyntheticEmbeddings()),self.provider)
        self.assertEqual(restarted.run(self.alice),'downloaded')
        self.assertEqual(store.retrieve(self.alice,'preference')[0]['id'],self.identity)
        self.assertEqual(store.retrieve(self.bob,'preference'),[])

    def test_deleted_memory_cannot_reappear_below_latest_trusted_floor_even_on_explicit_recovery(self):
        self.store.delete_memory(self.alice,self.identity); self.sync.run(self.alice)
        store,sync=self.fresh()
        sync.import_checkpoint(self.alice,self.sync.export_checkpoint(self.alice,confirm=True),confirm=True)
        sync.configure(self.alice,enabled=True,consent=True)
        with patch.object(self.provider,'head',return_value=self.first_head),self.assertRaises(SyncConflict): sync.run(self.alice,recover=True)
        self.assertEqual(store.list_memories(self.alice),[])
        restarted=MemorySynchronizer(MemoryStore(store.directory,embedder=SyntheticEmbeddings()),self.provider)
        with patch.object(self.provider,'head',return_value=None),self.assertRaises(SyncConflict): restarted.run(self.alice,recover=True)
        self.assertEqual(store.restore_owner(self.alice),0)

    def test_newer_authenticated_history_propagates_deletion_after_checkpoint(self):
        checkpoint=self.sync.export_checkpoint(self.alice,confirm=True)
        self.store.delete_memory(self.alice,self.identity); self.sync.run(self.alice)
        store,sync=self.fresh(); sync.import_checkpoint(self.alice,checkpoint,confirm=True)
        sync.configure(self.alice,enabled=True,consent=True)
        self.assertEqual(sync.run(self.alice),'downloaded')
        self.assertEqual(store.restore_owner(self.alice),0)
        self.assertEqual(store.retrieve(self.alice,'preference'),[])

    def test_same_revision_authenticated_fork_is_rejected(self):
        checkpoint=self.sync.export_checkpoint(self.alice,confirm=True)
        # A second valid revision-one publication with the same owner key is a fork.
        other_provider=MockCloudProvider(self.root/'fork')
        self.provider=other_provider
        store,sync=self.fresh()
        publisher=MemorySynchronizer(self.store,other_provider)
        with self.store._transaction() as db:
            state=self.store._sync_state(db,_owner(self.alice)); state.update(revision=0,identity=None,ack=None,pending=True)
            self.store._write_sync_state(db,_owner(self.alice),state)
        publisher.run(self.alice)
        sync.import_checkpoint(self.alice,checkpoint,confirm=True); sync.configure(self.alice,enabled=True,consent=True)
        with self.assertRaises(SyncConflict): sync.run(self.alice,recover=True)
        self.assertEqual(store.list_memories(self.alice),[])

    def test_export_refuses_unsynchronized_revocations_and_requires_confirmation(self):
        with self.assertRaises(PermissionError): self.sync.export_checkpoint(self.alice)
        self.store.delete_memory(self.alice,self.identity)
        with self.assertRaises(SyncConflict): self.sync.export_checkpoint(self.alice,confirm=True)
        self.sync.run(self.alice)
        self.assertIsInstance(self.sync.export_checkpoint(self.alice,confirm=True),bytes)

    def test_invalid_checkpoint_has_no_owner_state_or_key_mutation(self):
        checkpoint=self.sync.export_checkpoint(self.alice,confirm=True)
        store,sync=self.fresh(); filename=store.directory/('sync-'+_owner(self.alice)+'.key'); before=filename.read_bytes()
        cipher=self.sync._key(_owner(self.alice)); payload=json.loads(cipher.decrypt(checkpoint))
        for value in (b'SYNTHETIC-PRIVATE-TOKEN',checkpoint[:-1]+b'!',b'X'*4097,cipher.encrypt(encoded(payload|{'schema':True})),cipher.encrypt(encoded(payload|{'revision':False})),cipher.encrypt(encoded(payload|{'owner':_owner(self.bob)}))):
            with self.subTest(size=len(value)),self.assertRaises(SyncUnavailable) as failure:
                sync.import_checkpoint(self.alice,value,confirm=True)
            self.assertNotIn('PRIVATE-TOKEN',str(failure.exception))
        self.assertEqual(filename.read_bytes(),before)
        with closing(sqlite3.connect(store.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memory_sync').fetchone()[0],0)
        with self.assertRaises(PermissionError): sync.import_checkpoint(self.alice,checkpoint)

    def test_import_never_replaces_existing_checkpoint_or_populated_owner_vault(self):
        old=self.sync.export_checkpoint(self.alice,confirm=True)
        self.store.delete_memory(self.alice,self.identity); self.sync.run(self.alice)
        latest=self.sync.export_checkpoint(self.alice,confirm=True)
        store,sync=self.fresh(); sync.import_checkpoint(self.alice,latest,confirm=True)
        with self.assertRaises(SyncConflict): sync.import_checkpoint(self.alice,old,confirm=True)
        # Other owners retain their local records through import and recovery.
        bob=store.save_verified(self.bob,{'preference':'synthetic bob'}, {'source':'synthetic bob confirmation'},verified=True)
        sync.configure(self.alice,enabled=True,consent=True); sync.run(self.alice)
        self.assertEqual(store.list_memories(self.bob)[0]['id'],bob)
        with self.assertRaises(SyncConflict): self.sync.import_checkpoint(self.alice,old,confirm=True)

    def test_local_checkpoint_command_never_prompts_or_contacts_provider_and_refuses_overwrite(self):
        path=self.root/'trusted-checkpoint.encrypted'; output=StringIO()
        with override_settings(ALFRED_MEMORY_DIR=self.store.directory),patch.object(self.provider,'head',side_effect=AssertionError('No network')):
            call_command('memory_sync_checkpoint','export',user=self.alice.pk,file=str(path),confirm=True,stdout=output)
            before=path.read_bytes()
            with self.assertRaises(CommandError): call_command('memory_sync_checkpoint','export',user=self.alice.pk,file=str(path),confirm=True,stdout=output)
        self.assertEqual(path.read_bytes(),before)
        store,sync=self.fresh()
        with override_settings(ALFRED_MEMORY_DIR=store.directory):
            call_command('memory_sync_checkpoint','import',user=self.alice.pk,file=str(path),confirm=True,stdout=output)
        self.assertFalse(sync.status(self.alice)['enabled'])
        self.assertNotIn('SYNTHETIC-PRIVATE-CHECKPOINT',output.getvalue())
