"""SYNC-11: encrypted backup archives copied to Cloudflare R2, proven against a synthetic signed wire (no network)."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import hmac
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from django.test import SimpleTestCase, override_settings

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from alfred_private_storage import private_directory
from apps.ml_engine.services.memory_r2 import R2Bucket, signed_headers, validate_profile
from apps.ml_engine.services.memory_sync import SyncUnavailable
from scripts import cloud_backup
from scripts import release_recovery as recovery
from tests.test_memory_r2 import HOST, PROFILE, SETTINGS

NS = ' xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'


class MultipartR2Wire:
    """Checks each Signature V4 request like R2 and keeps objects, uploads and parts in memory."""

    def __init__(self):
        self.objects = {}; self.uploads = {}; self.calls = []; self.fail_part = None

    def request(self, method, url, *, headers, data=None, accepted_statuses=(200,), **kwargs):
        body = data or b''; outgoing = {k.lower(): v for k, v in headers.items()}; parts = urlsplit(url)
        self.calls.append((method, parts.path, parts.query))
        assert parts.scheme == 'https' and parts.hostname == HOST, url
        stamp = datetime.strptime(outgoing['x-amz-date'], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        selected = {k: outgoing[k] for k in outgoing['authorization'].split('SignedHeaders=')[1].split(',')[0].split(';')}
        if not hmac.compare_digest(signed_headers(method, url, body, validate_profile(PROFILE), selected, now=stamp)['Authorization'], outgoing['authorization']):
            raise PublicHTTPError('authorization_failed')
        key = parts.path.lstrip('/').partition('/')[2]; query = {k: v[0] for k, v in parse_qs(parts.query, keep_blank_values=True).items()}
        def reply(status, content=b'', kind='application/xml', extra=None):
            if status not in accepted_statuses: raise PublicHTTPError('api_error')
            return PublicResponse(content, kind, status, extra or {})
        if method == 'GET' and not key:
            rows = ''.join(f'<Contents><Key>{k}</Key><Size>{len(v)}</Size><LastModified>2026-11-06T00:00:00.000Z</LastModified></Contents>'
                           for k, v in sorted(self.objects.items()) if k.startswith(query['prefix']))
            return reply(200, f'<ListBucketResult{NS}><IsTruncated>false</IsTruncated>{rows}</ListBucketResult>'.encode())
        if method == 'POST' and 'uploads' in query:
            upload_id = 'synthetic-upload-' + str(len(self.uploads) + 1); self.uploads[upload_id] = {}
            return reply(200, f'<InitiateMultipartUploadResult{NS}><UploadId>{upload_id}</UploadId></InitiateMultipartUploadResult>'.encode())
        if method == 'PUT':
            number = int(query['partNumber'])
            if number == self.fail_part: raise OSError('SYNTHETIC-NETWORK-DOWN')
            self.uploads[query['uploadId']][number] = body
            return reply(200, b'', '', {'ETag': '"' + sha256(body).hexdigest()[:32] + '"'})
        if method == 'POST':
            stored = self.uploads.pop(query['uploadId']); sizes = [len(stored[n]) for n in sorted(stored)]
            assert body.count(b'<Part>') == len(stored) and len(set(sizes[:-1])) <= 1 and sizes[-1] <= sizes[0]
            self.objects[key] = b''.join(stored[n] for n in sorted(stored))
            return reply(200, f'<CompleteMultipartUploadResult{NS}><Key>{key}</Key></CompleteMultipartUploadResult>'.encode())
        if method == 'DELETE':
            self.uploads.pop(query['uploadId'], None); return reply(204, b'', '')
        start, end = map(int, outgoing['range'].removeprefix('bytes=').split('-'))
        return reply(206, self.objects[key][start:end + 1], 'application/octet-stream')


class CloudBackupTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temporary = TemporaryDirectory(prefix='alfred-cloud-backup-synthetic-'); cls.root = Path(cls.temporary.name)
        runtime = cls.root / 'runtime'; private_directory(runtime)
        for folder in ('config', 'media', 'artifacts/native'): (runtime / folder).mkdir(parents=True)
        (runtime / 'config/native.env').write_text('SYNTHETIC_ONLY=not-a-real-credential')
        (runtime / 'media/synthetic.txt').write_text('synthetic owned evidence ' * 400)
        for name in ('db.sqlite3', 'artifacts/native/jobs.sqlite3'):
            with closing(sqlite3.connect(runtime / name)) as db, db:
                db.execute('CREATE TABLE ledger (id INTEGER PRIMARY KEY, amount NUMERIC)'); db.execute("INSERT INTO ledger VALUES (1,'123.45')")
        cls.runtime = runtime; cls.key = cls.root / 'portable.key'; cls.key.write_bytes(Fernet.generate_key())
        cls.backup = cls.root / 'backup'
        recovery.create(runtime, cls.backup, cls.key, 'synthetic-release', 'a' * 40, 'b' * 40)
        cls.digest = recovery.release.sha256(cls.backup / 'recovery.zip')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup(); super().tearDownClass()

    def setUp(self):
        self.wire = MultipartR2Wire(); self.client = R2Bucket(PROFILE)
        for target in (patch('apps.ml_engine.services.memory_r2.request', self.wire.request), patch.object(cloud_backup, 'PART', 1024)):
            target.start(); self.addCleanup(target.stop)

    def upload(self, **kwargs):
        return cloud_backup.upload(self.backup, kwargs.pop('key', self.key), recovery_copy_confirmed=kwargs.pop('confirmed', True), client=self.client)

    def test_upload_is_ciphertext_verified_and_restores_after_download(self):
        receipt = self.upload()
        self.assertEqual(receipt['OFF_DEVICE_COPY_VERIFIED'], 'PASS'); self.assertFalse(receipt['already_present'])
        stored = self.wire.objects['alfred-backup-v1/' + self.digest + '.zip']
        self.assertEqual(stored, (self.backup / 'recovery.zip').read_bytes())
        for secret in (b'synthetic owned evidence', b'123.45', b'not-a-real-credential', b'synthetic.txt', b'ledger'):
            self.assertNotIn(secret, stored)
        self.assertGreater(sum(call[0] == 'PUT' for call in self.wire.calls), 2)  # really multipart
        self.assertTrue(self.upload()['already_present'])
        self.assertEqual(sum(call[0] == 'POST' and 'uploads' in call[2] for call in self.wire.calls), 1)
        fetched = cloud_backup.download(self.digest, self.key, self.root / 'downloaded-1', client=self.client)
        self.assertEqual(fetched['CLOUD_DOWNLOAD_VERIFIED'], 'PASS')
        restored = self.root / 'restored-1'
        self.assertEqual(recovery.restore(self.root / 'downloaded-1', self.key, restored)['financial_reconciliation'], 'PASS')
        self.assertEqual(recovery.database_snapshot(restored / 'db.sqlite3'), recovery.database_snapshot(self.runtime / 'db.sqlite3'))
        self.assertEqual((restored / 'media/synthetic.txt').read_bytes(), (self.runtime / 'media/synthetic.txt').read_bytes())

    def test_upload_needs_a_confirmed_portable_key_that_opens_the_backup(self):
        with self.assertRaisesMessage(recovery.release.GateError, 'key_recovery_copy_unconfirmed'):
            self.upload(confirmed=False)
        wrong = self.root / 'wrong.key'
        if not wrong.exists(): wrong.write_bytes(Fernet.generate_key())
        with self.assertRaisesMessage(recovery.release.GateError, 'key_does_not_open_backup'):
            self.upload(key=wrong)
        bound = self.root / 'profile-bound.key'
        if not bound.exists(): bound.write_bytes(b'M15DPAPI1\0synthetic')
        with patch.object(recovery, 'protect_key', return_value=self.key.read_bytes()), \
                self.assertRaisesMessage(recovery.release.GateError, 'portable_key_required'):
            self.upload(key=bound)
        self.assertEqual(self.wire.calls, [])  # nothing reached the cloud

    def test_activation_needs_the_owner_flag_and_a_valid_profile(self):
        with override_settings(ALFRED_CLOUD_BACKUP_AUTHORIZED=False, **SETTINGS), \
                self.assertRaisesMessage(recovery.release.GateError, 'cloud_backup_not_authorized'):
            cloud_backup.bucket()
        with override_settings(ALFRED_CLOUD_BACKUP_AUTHORIZED=True, **(SETTINGS | {'ALFRED_MEMORY_R2_SECRET_KEY': ''})), \
                self.assertRaisesMessage(recovery.release.GateError, 'r2_profile_missing_or_invalid'):
            cloud_backup.bucket()
        with override_settings(ALFRED_CLOUD_BACKUP_AUTHORIZED=True, **SETTINGS):
            self.assertEqual(cloud_backup.bucket().base, f"https://{HOST}/{PROFILE['bucket']}")

    def test_interrupted_upload_is_aborted_and_a_damaged_copy_never_counts(self):
        before = (self.backup / 'recovery.zip').read_bytes()
        self.wire.fail_part = 2
        with self.assertRaises(SyncUnavailable):
            self.upload()
        self.assertEqual(self.wire.objects, {}); self.assertEqual(self.wire.uploads, {})  # parts aborted
        self.assertEqual(self.wire.calls[-1][0], 'DELETE')
        self.assertEqual((self.backup / 'recovery.zip').read_bytes(), before)
        self.wire.fail_part = None; name = 'alfred-backup-v1/' + self.digest + '.zip'
        self.wire.objects[name] = before[:-1] + bytes([before[-1] ^ 1])  # same size, one bit flipped
        with self.assertRaisesMessage(recovery.release.GateError, 'off_device_copy_verification_failed'):
            self.upload()
        with self.assertRaisesMessage(recovery.release.GateError, 'cloud_archive_hash_failed'):
            cloud_backup.download(self.digest, self.key, self.root / 'downloaded-damaged', client=self.client)
        with self.assertRaisesMessage(recovery.release.GateError, 'cloud_archive_missing'):
            cloud_backup.download('f' * 64, self.key, self.root / 'downloaded-missing', client=self.client)

    def test_new_key_is_portable_and_never_overwrites(self):
        path = self.root / 'new-backup.key'
        if path.exists(): path.unlink()
        self.assertEqual(cloud_backup.new_key(path)['key_kind'], 'PORTABLE_FORMAT_UNVERIFIED')
        self.assertEqual(recovery.cipher_from_file(path)[1], 'PORTABLE_FORMAT_UNVERIFIED')
        with self.assertRaises(FileExistsError):
            cloud_backup.new_key(path)
        with self.assertRaisesMessage(recovery.release.GateError, 'key_must_stay_outside_repository'):
            cloud_backup.new_key(cloud_backup.ROOT / 'artifacts' / 'never.key')
