"""SYNC-02: encrypted memory sync to Cloudflare R2, proven against a synthetic signed wire (no network)."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import hmac
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.ml_engine.services.memory_cloud import configured_provider, synchronizer
from apps.ml_engine.services.memory_r2 import R2MemoryProvider, signed_headers, validate_profile
from apps.ml_engine.services.memory_sync import MemorySynchronizer, SyncConflict, SyncUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from tests.test_persistent_memory import SyntheticEmbeddings

# Made-up values in R2's formats; never a real account or token.
PROFILE = {'account_id': 'a' * 32, 'bucket': 'synthetic-alfred-sync', 'access_key': 'SYNTHETICACCESSKEY01',
           'secret_key': 'SYNTHETIC-secret-key-0123456789abcdef', 'jurisdiction': ''}
SETTINGS = {'ALFRED_MEMORY_R2_' + key.upper(): value for key, value in PROFILE.items()}
HOST = PROFILE['account_id'] + '.r2.cloudflarestorage.com'


class SignedR2Wire:
    """Checks every Signature V4 request like R2 would and keeps objects in SQLite."""

    def __init__(self, database):
        self.database = database; self.calls = []; self.offline = False; self.before_head = None
        with closing(sqlite3.connect(database)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS objects(key TEXT PRIMARY KEY, body BLOB, etag TEXT, created REAL)')

    def respond(self, status, body=b'', content_type='application/xml', headers=None, *, accepted):
        if status in (401, 403): raise PublicHTTPError('authorization_failed')  # what public_http raises
        if status not in accepted: raise PublicHTTPError('api_error')
        return PublicResponse(body, content_type, status, headers or {})

    def request(self, method, url, *, headers, data=None, accepted_statuses=(200,), **kwargs):
        self.calls.append((method, url, dict(headers)))
        if self.offline: raise OSError('SYNTHETIC-NETWORK-DOWN')
        body = data or b''; outgoing = {k.lower(): v for k, v in headers.items()}
        parts = urlsplit(url)
        assert parts.scheme == 'https' and parts.hostname == HOST, url
        stamp = datetime.strptime(outgoing['x-amz-date'], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        selected = {k: outgoing[k] for k in outgoing['authorization'].split('SignedHeaders=')[1].split(',')[0].split(';')}
        expected = signed_headers(method, url, body, validate_profile(PROFILE), selected, now=stamp)['Authorization']
        if not hmac.compare_digest(expected, outgoing['authorization']) or '/auto/s3/' not in outgoing['authorization']:
            return self.respond(403, accepted=accepted_statuses)
        bucket, _, key = parts.path.lstrip('/').partition('/')
        assert bucket == PROFILE['bucket']
        with closing(sqlite3.connect(self.database)) as db:
            db.execute('BEGIN IMMEDIATE')
            if not key and method == 'GET':
                prefix = parse_qs(parts.query)['prefix'][0]
                rows = db.execute('SELECT key, created FROM objects WHERE key LIKE ?', (prefix + '%',)).fetchall()
                xml = '<ListBucketResult><IsTruncated>false</IsTruncated>' + ''.join(
                    '<Contents><Key>' + k + '</Key><LastModified>' + datetime.fromtimestamp(t, timezone.utc).isoformat() + '</LastModified></Contents>' for k, t in rows) + '</ListBucketResult>'
                return self.respond(200, xml.encode(), accepted=accepted_statuses)
            row = db.execute('SELECT body, etag FROM objects WHERE key=?', (key,)).fetchone()
            if method == 'GET':
                if not row: return self.respond(404, accepted=accepted_statuses)
                return self.respond(200, row[0], 'application/octet-stream', {'ETag': row[1]}, accepted=accepted_statuses)
            if method == 'DELETE':
                db.execute('DELETE FROM objects WHERE key=?', (key,)); db.commit()
                return self.respond(204, b'', '', accepted=accepted_statuses)
            assert method == 'PUT' and outgoing['content-type'] == 'application/octet-stream'
            assert not any(name.startswith('x-amz-server-side') or name == 'x-amz-expected-bucket-owner' for name in outgoing)
            if key.endswith('/head') and self.before_head:
                self.before_head(); return self.respond(412, accepted=accepted_statuses)
            if (outgoing.get('if-none-match') == '*' and row) or ('if-match' in outgoing and (not row or row[1] != outgoing['if-match'])):
                return self.respond(412, accepted=accepted_statuses)
            etag = '"' + sha256(body).hexdigest()[:32] + '"'
            db.execute('INSERT INTO objects VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET body=excluded.body, etag=excluded.etag, created=excluded.created',
                       (key, body, etag, time.time())); db.commit()
            return self.respond(200, b'', '', {'ETag': etag}, accepted=accepted_statuses)


class R2MemorySyncTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-r2-synthetic-')))
        self.enterContext(override_settings(ALFRED_ABUSE_THROTTLE_DIR=str(self.root / 'request-limits')))
        self.alice = get_user_model().objects.create_user(username='synthetic-r2-alice')
        self.store = MemoryStore(self.root / 'one', embedder=SyntheticEmbeddings()); self.owner = _owner(self.alice)
        self.wire = SignedR2Wire(self.root / 'wire.sqlite3')
        self.enterContext(patch('apps.ml_engine.services.memory_r2.request', side_effect=self.wire.request))
        self.provider = R2MemoryProvider(self.owner, PROFILE); self.sync = MemorySynchronizer(self.store, self.provider)
        self.sync.configure(self.alice, enabled=True, consent=True)

    def save(self, text='SYNTHETIC-PRIVATE-MOUNTAIN'):
        return self.store.save_verified(self.alice, {'preference': text}, {'source': 'synthetic r2 confirmation', 'reference': uuid4().hex}, verified=True)

    def retry(self):
        with self.store._transaction() as db:
            state = self.store._sync_state(db, self.owner); state['retry_at'] = 0; self.store._write_sync_state(db, self.owner, state)

    def test_profile_accepts_only_r2_shaped_values_and_builds_the_endpoint_itself(self):
        for change in ({'account_id': 'not-hex'}, {'account_id': 'A' * 32}, {'bucket': 'foo.example'}, {'bucket': 'Upper'},
                       {'secret_key': 'short'}, {'jurisdiction': 'us'}, {'access_key': 'bad key'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_profile(PROFILE | change)
        with self.assertRaises(ValueError):
            validate_profile(PROFILE | {'endpoint': 'https://127.0.0.1'})
        self.assertEqual(self.provider.base, f"https://{HOST}/{PROFILE['bucket']}")
        self.assertEqual(R2MemoryProvider(self.owner, PROFILE | {'jurisdiction': 'eu'}).base,
                         f"https://{PROFILE['account_id']}.eu.r2.cloudflarestorage.com/{PROFILE['bucket']}")

    def test_provider_needs_the_owner_flag_and_a_complete_profile(self):
        with override_settings(ALFRED_MEMORY_SYNC_PROVIDER='r2', ALFRED_MEMORY_CLOUD_AUTHORIZED=False, **SETTINGS):
            self.assertEqual(configured_provider(), '')
            with self.assertRaises(SyncUnavailable): synchronizer(self.store, self.alice)
        with override_settings(ALFRED_MEMORY_SYNC_PROVIDER='r2', ALFRED_MEMORY_CLOUD_AUTHORIZED=True, **(SETTINGS | {'ALFRED_MEMORY_R2_SECRET_KEY': ''})):
            self.assertEqual(configured_provider(), '')
        with override_settings(ALFRED_MEMORY_SYNC_PROVIDER='r2', ALFRED_MEMORY_CLOUD_AUTHORIZED=True, **SETTINGS):
            self.assertEqual(configured_provider(), 'r2')
            self.assertIsInstance(synchronizer(self.store, self.alice).provider, R2MemoryProvider)
            self.client.force_login(self.alice)
            self.assertEqual({k: v for k, v in self.client.get('/api/ai/memories/sync/').json().items() if k != 'status'},
                             {'provider': 'r2', 'available': True})
        self.assertEqual(self.wire.calls, [])  # choosing a provider never contacts it

    def test_upload_then_a_second_pc_downloads_and_only_ciphertext_reaches_r2(self):
        identity = self.save(); self.assertEqual(self.sync.run(self.alice), 'uploaded')
        other = MemoryStore(self.root / 'two', embedder=SyntheticEmbeddings()); key = 'sync-' + self.owner + '.key'
        (other.directory / key).write_bytes((self.store.directory / key).read_bytes())
        sync = MemorySynchronizer(other, R2MemoryProvider(self.owner, PROFILE))
        sync.import_checkpoint(self.alice, self.sync.export_checkpoint(self.alice, confirm=True), confirm=True)
        sync.configure(self.alice, enabled=True, consent=True)
        self.assertEqual(sync.run(self.alice), 'downloaded')
        self.assertEqual(other.retrieve(self.alice, 'mountain')[0]['id'], identity)
        self.assertNotIn(b'SYNTHETIC-PRIVATE-MOUNTAIN', (self.root / 'wire.sqlite3').read_bytes())
        self.assertTrue(all(urlsplit(url).path.startswith('/' + PROFILE['bucket'] + '/alfred-memory-v1/' + self.owner)
                            or 'prefix=alfred-memory-v1%2F' + self.owner in url for _, url, _ in self.wire.calls))

    def test_refused_or_unreachable_r2_keeps_local_data_and_never_reveals_the_secret(self):
        self.save()
        bad = R2MemoryProvider(self.owner, PROFILE | {'secret_key': 'SYNTHETIC-WRONG-secret-0123456789abcdef'})
        with self.assertRaises(SyncUnavailable) as failure: MemorySynchronizer(self.store, bad).run(self.alice)
        self.assertNotIn('SYNTHETIC', str(failure.exception)); self.assertNotIn('secret', str(failure.exception).lower())
        self.retry(); self.wire.offline = True
        with self.assertRaises(SyncUnavailable): self.sync.run(self.alice)
        self.assertTrue(self.sync.status(self.alice)['pending'])
        self.assertEqual(len(self.store.list_memories(self.alice)), 1)
        self.wire.offline = False; self.retry()
        self.assertEqual(self.sync.run(self.alice), 'uploaded')

    def test_head_race_is_a_conflict_and_old_snapshots_are_never_overwritten(self):
        self.save(); self.wire.before_head = lambda: None
        with self.assertRaises(SyncConflict): self.sync.run(self.alice)
        self.assertEqual(self.sync.status(self.alice)['revision'], 0)
        self.wire.before_head = None; self.retry()
        self.assertEqual(self.sync.run(self.alice), 'uploaded')
        head = self.provider.head(self.owner, deadline=time.monotonic() + 5)
        body = self.provider.download(self.owner, head['identity'], deadline=time.monotonic() + 5)
        # Re-publishing the same immutable object is verified (412 + download), never rewritten.
        self.assertEqual(self.provider.publish(self.owner, 1, head['identity'], body, head['manifest'], deadline=time.monotonic() + 5)['revision'], 2)

    def test_pruning_deletes_only_this_owners_unreferenced_snapshots(self):
        self.save(); self.sync.run(self.alice); orphan = 'b' * 64; other_owner = 'c' * 64
        with closing(sqlite3.connect(self.wire.database)) as db:
            for key in (self.provider.prefix + 'snapshots/' + orphan, 'alfred-memory-v1/' + other_owner + '/snapshots/' + orphan):
                db.execute('INSERT INTO objects VALUES(?,?,?,?)', (key, b'old ciphertext', '"old"', time.time() - 40 * 86400))
            db.commit()
        self.assertEqual(self.sync.prune(self.alice, confirm=True), 1)
        with closing(sqlite3.connect(self.wire.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM objects WHERE key LIKE ?', ('%' + other_owner + '%',)).fetchone()[0], 1)
