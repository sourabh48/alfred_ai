from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
from uuid import uuid4
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from apps.ml_engine.services.memory_cloud import synchronizer, configured_provider
from apps.ml_engine.services.memory_sync import MemorySynchronizer, SyncConflict, SyncUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from tests.memory_s3_fixture import PROFILE, SignedS3Fixture, LegacyS3FixtureProvider as S3MemoryProvider, signed_headers, validate_profile
from tests.test_persistent_memory import SyntheticEmbeddings


class MemoryCloudTests(TestCase):
    """Historical wire-only contract; this adapter is absent from application runtime."""
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-s3-synthetic-')))
        self.enterContext(override_settings(ALFRED_ABUSE_THROTTLE_DIR=str(self.root/'request-limits')))
        self.alice=get_user_model().objects.create_user(username='synthetic-s3-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-s3-bob')
        self.store=MemoryStore(self.root/'one',embedder=SyntheticEmbeddings()); self.owner=_owner(self.alice)
        self.wire=SignedS3Fixture(self.root/'wire.sqlite3')
        self.enterContext(patch('tests.memory_s3_fixture.request',side_effect=self.wire.request))
        self.provider=S3MemoryProvider(self.owner,PROFILE); self.sync=MemorySynchronizer(self.store,self.provider)
        self.sync.configure(self.alice,enabled=True,consent=True)

    def save(self):
        return self.store.save_verified(self.alice,{'preference':'SYNTHETIC-PRIVATE-MOUNTAIN'}, {'source':'synthetic cloud confirmation','reference':uuid4().hex},verified=True)

    def second(self):
        store=MemoryStore(self.root/'two',embedder=SyntheticEmbeddings()); filename='sync-'+self.owner+'.key'
        (store.directory/filename).write_bytes((self.store.directory/filename).read_bytes())
        sync=MemorySynchronizer(store,S3MemoryProvider(self.owner,PROFILE))
        sync.import_checkpoint(self.alice,self.sync.export_checkpoint(self.alice,confirm=True),confirm=True)
        sync.configure(self.alice,enabled=True,consent=True)
        return store,sync

    def retry(self):
        with self.store._transaction() as db:
            state=self.store._sync_state(db,self.owner); state['retry_at']=0; self.store._write_sync_state(db,self.owner,state)

    def test_official_signature_vector(self):
        result=signed_headers('GET','https://examplebucket.s3.amazonaws.com/test.txt',b'',PROFILE,{'Range':'bytes=0-9'},now=datetime(2013,5,24,tzinfo=timezone.utc))
        self.assertTrue(result['Authorization'].endswith('Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41'))

    def test_config_rejects_arbitrary_destinations_credentials_and_owners(self):
        for change in ({'bucket':'foo.example'}, {'bucket':'127.0.0.1'}, {'region':'us-east-1.attacker'}, {'account':'other'}, {'secret_key':'bad'}, {'session_token':'bad\nheader'}, {'endpoint':'http://127.0.0.1'}):
            with self.subTest(change=change),self.assertRaises(ValueError): validate_profile(PROFILE|change)
        with self.assertRaises(PermissionError): self.provider.head(_owner(self.bob),deadline=time.monotonic()+5)
        self.assertEqual(self.wire.calls,0)

    def test_private_nonversioned_owner_enforced_bucket_required(self):
        for change in ({'version':'Enabled'},{'version':'Suspended'},{'public':False},{'ownership':'ObjectWriter'}):
            for k,v in change.items(): setattr(self.wire,k,v)
            with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
            self.wire.version=''; self.wire.public=True; self.wire.ownership='BucketOwnerEnforced'; self.retry()
        self.assertFalse(self.provider.checked)

    def test_authentication_failure_preserves_local_data_and_safe_errors(self):
        self.save(); self.provider.profile['secret_key']='SYNTHETIC-WRONG-SECRET-12345678901234567890'
        with self.assertRaises(SyncUnavailable) as failure: self.sync.run(self.alice)
        self.assertNotIn('SECRET',str(failure.exception)); self.assertTrue(self.sync.status(self.alice)['pending'])
        self.assertEqual(len(self.store.list_memories(self.alice)),1)

    def test_signed_upload_restart_download_verify_retrieve(self):
        identity=self.save(); self.assertEqual(self.sync.run(self.alice),'uploaded')
        other,sync=self.second(); self.assertEqual(sync.run(self.alice),'downloaded')
        self.assertEqual(other.retrieve(self.alice,'mountain')[0]['id'],identity); self.assertEqual(other.restore_owner(self.alice),1)
        self.assertEqual(other.retrieve(self.bob,'mountain'),[])
        self.assertNotIn(b'SYNTHETIC-PRIVATE-MOUNTAIN',(self.root/'wire.sqlite3').read_bytes())

    def test_offline_and_interrupted_uploads_are_durable_and_retryable(self):
        self.save(); self.wire.offline=True
        with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        self.wire.offline=False; self.retry(); self.wire.fail_head_once=True
        with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        self.assertTrue(self.sync.status(self.alice)['pending']); self.retry()
        self.assertEqual(self.sync.run(self.alice),'uploaded'); self.assertEqual(self.sync.status(self.alice)['revision'],1)

    def test_lost_ack_and_duplicate_object_are_idempotent(self):
        self.save(); self.wire.lose_ack_once=True
        with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        self.retry(); self.assertEqual(self.sync.run(self.alice),'current')
        self.assertEqual(self.sync.status(self.alice)['revision'],1)
        head=self.provider.head(self.owner,deadline=time.monotonic()+5); body=self.provider.download(self.owner,head['identity'],deadline=time.monotonic()+5)
        self.assertEqual(self.provider.publish(self.owner,1,head['identity'],body,head['manifest'],deadline=time.monotonic()+5)['revision'],2)

    def test_partial_or_corrupt_download_does_not_replace_index(self):
        self.save(); self.sync.run(self.alice); other,sync=self.second(); self.wire.partial=True
        with self.assertRaises(SyncUnavailable): sync.run(self.alice)
        self.assertEqual(other.list_memories(self.alice),[]); self.wire.partial=False
        with closing(sqlite3.connect(self.wire.database)) as db:
            db.execute("UPDATE wire_objects SET body=? WHERE key LIKE '%/snapshots/%'",(b'corrupt encrypted bytes',)); db.commit()
        with other._transaction() as db:
            state=other._sync_state(db,self.owner); state['retry_at']=0; other._write_sync_state(db,self.owner,state)
        with self.assertRaises(SyncUnavailable): sync.run(self.alice)

    def test_conflicting_updates_require_confirmation_and_merge_valid_data(self):
        first=self.save(); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        remote=other.save_verified(self.alice,{'preference':'synthetic beach'},{'source':'synthetic review'},verified=True); sync.run(self.alice)
        local=self.save()
        with self.assertRaises(SyncConflict): self.sync.run(self.alice)
        self.assertEqual(self.sync.run(self.alice,recover=True),'uploaded')
        self.assertEqual({r['id'] for r in self.store.list_memories(self.alice)},{first,remote,local})

    def test_cas_race_retains_pending_and_immutable_ciphertext(self):
        self.save(); self.wire.before_head=lambda:None
        with self.assertRaises(SyncConflict): self.sync.run(self.alice)
        self.assertTrue(self.sync.status(self.alice)['pending']); self.assertEqual(self.sync.status(self.alice)['revision'],0)

    def test_tombstones_reset_and_old_snapshot_cannot_resurrect(self):
        identity=self.save(); self.sync.run(self.alice); other,sync=self.second(); sync.run(self.alice)
        old=self.provider.head(self.owner,deadline=time.monotonic()+5)
        self.store.delete_memory(self.alice,identity); self.sync.run(self.alice); sync.run(self.alice)
        self.assertEqual(other.list_memories(self.alice),[]); self.assertEqual(other.restore_owner(self.alice),0)
        with patch.object(self.provider,'head',return_value=old),self.assertRaises(SyncConflict): self.sync.run(self.alice)
        self.assertEqual(self.store.list_memories(self.alice),[])

    def test_pruning_keeps_current_ancestors_and_other_owners(self):
        self.save(); self.sync.run(self.alice)
        head=self.provider.head(self.owner,deadline=time.monotonic()+5); orphan='a'*64
        with closing(sqlite3.connect(self.wire.database)) as db:
            for key in (self.provider.prefix+'snapshots/'+orphan,'alfred-memory-v1/'+_owner(self.bob)+'/snapshots/'+orphan):
                db.execute('INSERT INTO wire_objects VALUES(?,?,?,?)',(key,b'old ciphertext','"old"',time.time()-40*86400))
            db.commit()
        with self.assertRaises(PermissionError): self.sync.prune(self.alice)
        self.assertEqual(self.sync.prune(self.alice,confirm=True),1); self.assertEqual(self.sync.prune(self.alice,confirm=True),0)
        self.assertTrue(self.provider.download(self.owner,head['identity'],deadline=time.monotonic()+5))
        with closing(sqlite3.connect(self.wire.database)) as db: self.assertEqual(db.execute("SELECT COUNT(*) FROM wire_objects WHERE key LIKE ?",('%'+_owner(self.bob)+'%',)).fetchone()[0],1)

    def test_disabled_real_factory_and_tick_never_contact_provider(self):
        with override_settings(ALFRED_MEMORY_SYNC_PROVIDER='s3',ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALFRED_MEMORY_DIR=str(self.store.directory)):
            with self.assertRaises(SyncUnavailable): synchronizer(self.store,self.alice)
            call_command('sync_private_memory',stdout=StringIO())
        self.assertEqual(self.wire.calls,0)

    def test_pruning_retains_129_authenticated_versions_and_refuses_dirty_or_changed_head(self):
        self.save(); self.sync.run(self.alice)
        for _ in range(129):
            self.store.set_retention(self.alice,29 if self.store.retention_days(self.alice)==30 else 30)
            self.sync.run(self.alice)
        with closing(sqlite3.connect(self.wire.database)) as db:
            db.execute('UPDATE wire_objects SET created=?',(time.time()-40*86400,)); db.commit()
        self.assertEqual(self.sync.prune(self.alice,confirm=True),1)
        with closing(sqlite3.connect(self.wire.database)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM wire_objects WHERE key LIKE '%/snapshots/%'").fetchone()[0],129)
        self.save()
        with self.assertRaises(SyncConflict): self.sync.prune(self.alice,confirm=True)

    def test_mock_snapshot_pruning_restores_immutability_and_current_recovery(self):
        from apps.ml_engine.services.memory_sync import MockCloudProvider
        provider=MockCloudProvider(self.root/'mock'); sync=MemorySynchronizer(self.store,provider)
        self.save(); sync.run(self.alice); orphan='b'*64
        with closing(sqlite3.connect(provider.database)) as db:
            db.execute('INSERT INTO objects VALUES(?,?,?)',(self.owner,orphan,b'old ciphertext'))
            db.execute('INSERT INTO object_times VALUES(?,?,?)',(self.owner,orphan,time.time()-40*86400)); db.commit()
        self.assertEqual(sync.prune(self.alice,confirm=True),1)
        with closing(sqlite3.connect(provider.database)) as db,self.assertRaises(sqlite3.IntegrityError):
            db.execute('DELETE FROM objects')
        self.assertEqual(self.store.restore_owner(self.alice),1)

    def test_aws_provisioning_and_historical_opt_in_are_disabled_without_mutation(self):
        self.sync.configure(self.alice,enabled=False)
        with self.store._transaction() as db:
            state=self.store._sync_state(db,self.owner); state['cloud']=PROFILE
            self.store._write_sync_state(db,self.owner,state)
        before=(self.store.directory/'verified.sqlite3').read_bytes()
        with patch('getpass.getpass',side_effect=AssertionError('No credential prompt')),self.assertRaises(CommandError):
            call_command('configure_memory_cloud',user=self.alice.pk,bucket=PROFILE['bucket'],region=PROFILE['region'],account=PROFILE['account'],stdout=StringIO())
        with override_settings(ALFRED_MEMORY_SYNC_PROVIDER='s3',ALFRED_MEMORY_CLOUD_AUTHORIZED=True,
                               ALFRED_MEMORY_SYNC_MOCK_DIR=str(self.root/'mock')):
            self.assertEqual(configured_provider(),'')
            with self.assertRaises(SyncUnavailable): synchronizer(self.store,self.alice)
        self.assertEqual((self.store.directory/'verified.sqlite3').read_bytes(),before)
        self.assertEqual(self.wire.calls,0)

    def test_runtime_has_no_aws_transport_and_api_reports_disabled(self):
        from apps.ml_engine.services import memory_cloud
        self.assertFalse(hasattr(memory_cloud,'S3MemoryProvider'))
        with override_settings(ALFRED_MEMORY_DIR=str(self.store.directory),ALFRED_MEMORY_SYNC_PROVIDER='s3',
                               ALFRED_MEMORY_CLOUD_AUTHORIZED=True), \
             patch('alfred_ai.services.public_http.request',side_effect=AssertionError('No external request')):
            self.client.force_login(self.alice)
            response=self.client.get('/api/ai/memories/sync/')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['provider'],'disabled')
            self.assertFalse(response.json()['available'])
            self.assertEqual(self.client.post('/api/ai/memories/sync/',{'action':'sync'},content_type='application/json').status_code,503)
            output=StringIO();call_command('sync_private_memory',stdout=output)
            self.assertIn('disabled',output.getvalue())
        self.assertEqual(self.wire.calls,0)
