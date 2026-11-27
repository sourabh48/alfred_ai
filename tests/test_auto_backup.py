"""SYNC-09/RUNTIME-08 (owner 2026-11-26): the locked key copy in R2 and the nightly encrypted backup, on synthetic data only."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hmac
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from alfred_ai.services import auto_backup, backup_key
from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from alfred_private_storage import private_directory
from apps.ml_engine.services.memory_sync import SyncUnavailable
from apps.ml_engine.services.memory_r2 import R2Bucket, signed_headers, validate_profile
from scripts import cloud_backup
from scripts import release_recovery as recovery
from tests.test_cloud_backup import MultipartR2Wire
from tests.test_memory_r2 import PROFILE, SETTINGS

PASS = "four unrelated synthetic words"


class ObjectR2Wire(MultipartR2Wire):
    """Adds plain object PUT, whole GET (404 when missing), object DELETE and the unfinished-upload list to the signed wire."""

    def __init__(self):
        super().__init__()
        self.started = {}  # upload id -> (key, initiated), for uploads the test leaves unfinished

    def request(self, method, url, *, headers, data=None, accepted_statuses=(200,), **kwargs):
        parts = urlsplit(url); key = parts.path.lstrip("/").partition("/")[2]
        outgoing = {k.lower(): v for k, v in headers.items()}
        if method == "GET" and not key and "uploads" in parse_qs(parts.query, keep_blank_values=True):
            super().request(method, url, headers=headers, data=data, accepted_statuses=accepted_statuses, **kwargs)  # signature
            rows = "".join(f"<Upload><Key>{k}</Key><UploadId>{u}</UploadId><Initiated>{t}</Initiated></Upload>"
                           for u, (k, t) in self.started.items() if u in self.uploads)
            return PublicResponse(f'<ListMultipartUploadsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">{rows}'
                                  '</ListMultipartUploadsResult>'.encode(), "application/xml", 200)
        if parts.query or not key or (method == "GET" and "range" in outgoing) or method == "POST":
            return super().request(method, url, headers=headers, data=data, accepted_statuses=accepted_statuses, **kwargs)
        self.calls.append((method, parts.path, ""))
        stamp = datetime.strptime(outgoing["x-amz-date"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        selected = {k: outgoing[k] for k in outgoing["authorization"].split("SignedHeaders=")[1].split(",")[0].split(";")}
        if not hmac.compare_digest(signed_headers(method, url, data or b"", validate_profile(PROFILE), selected, now=stamp)["Authorization"],
                                   outgoing["authorization"]):
            raise PublicHTTPError("authorization_failed")
        def reply(status, content=b""):
            if status not in accepted_statuses:
                raise PublicHTTPError("api_error")
            return PublicResponse(content, "application/octet-stream", status)
        if method == "PUT":
            self.objects[key] = data
            return reply(200)
        if method == "DELETE":
            self.objects.pop(key, None)
            return reply(204)
        return reply(200, self.objects[key]) if key in self.objects else reply(404)


def synthetic_runtime(root):
    runtime = root / "runtime"
    private_directory(runtime)
    for folder in ("config", "media", "artifacts/native"):
        (runtime / folder).mkdir(parents=True)
    (runtime / "config/local.env").write_text("SYNTHETIC_ONLY=not-a-real-credential")
    (runtime / "media/synthetic.txt").write_text("synthetic owned evidence " * 200)
    for name in ("db.sqlite3", "artifacts/native/jobs.sqlite3"):
        with closing(sqlite3.connect(runtime / name)) as db, db:
            db.execute("CREATE TABLE ledger (id INTEGER PRIMARY KEY, owner TEXT, amount NUMERIC)")
            db.execute("INSERT INTO ledger VALUES (1, 'alice', '123.45'), (2, 'bob', '67.89')")
    return runtime


class Clock:
    def __init__(self):
        self.moment = datetime(2026, 11, 26, 20, 15, tzinfo=timezone.utc)

    def now(self, tz=None):
        self.moment += timedelta(days=1)
        return self.moment


class R2Setup(SimpleTestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-auto-backup-synthetic-")))
        self.runtime = synthetic_runtime(self.root)
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.runtime)}))
        self.enterContext(patch.object(backup_key, "SCRYPT_N", 2 ** 10))
        self.enterContext(override_settings(ALFRED_CLOUD_BACKUP_AUTHORIZED=True, **SETTINGS))
        self.wire = ObjectR2Wire()
        self.enterContext(patch("apps.ml_engine.services.memory_r2.request", self.wire.request))
        self.enterContext(patch.object(cloud_backup, "PART", 1024))
        self.client = R2Bucket(PROFILE)


class KeyCopyInR2Tests(R2Setup):
    def test_save_reads_back_and_a_new_pc_fetches_and_opens_it(self):
        backup_key.make(PASS, PASS)
        key = backup_key.key_path().read_bytes()
        self.assertTrue(backup_key.save_to_r2()["in_r2"])  # no client given: the configured bucket
        stored = self.wire.objects[backup_key.R2_NAME]
        self.assertNotIn(key, stored)
        self.assertNotIn(PASS.encode(), stored)
        new_pc = self.root / "new-pc"
        with patch.dict(os.environ, {"ALFRED_DATA_DIR": str(new_pc)}):
            self.assertFalse(backup_key.status()["key"])
            fetched = backup_key.fetch_from_r2(self.client)
            self.assertTrue(fetched["locked_copy"] and fetched["in_r2"] and not fetched["key"])
            with self.assertRaises(backup_key.BackupKeyError):
                backup_key.restore("a wrong synthetic passphrase")
            self.assertTrue(backup_key.restore(PASS)["key"])
            self.assertEqual(backup_key.key_path().read_bytes(), key)

    def test_missing_copy_damaged_copy_and_no_setup_are_plain_messages(self):
        with self.assertRaisesRegex(backup_key.BackupKeyError, "No ALFRED backup key copy"):
            backup_key.fetch_from_r2(self.client)
        self.wire.objects[backup_key.R2_NAME] = b"not json"
        with self.assertRaisesRegex(backup_key.BackupKeyError, "not an ALFRED backup key copy"):
            backup_key.fetch_from_r2(self.client)
        with self.assertRaisesRegex(backup_key.BackupKeyError, "Make the locked copy first"):
            backup_key.save_to_r2(self.client)
        backup_key.make(PASS, PASS)
        with override_settings(ALFRED_CLOUD_BACKUP_AUTHORIZED=False), \
                self.assertRaisesRegex(backup_key.BackupKeyError, "not set up yet"):
            backup_key.save_to_r2()


class NightlyBackupTests(R2Setup):
    def ready(self):
        backup_key.make(PASS, PASS)
        backup_key.save_to_r2(self.client)

    def archives(self):
        return sorted(k for k in self.wire.objects if k.startswith(cloud_backup.PREFIX))

    def test_nothing_runs_until_the_key_copy_is_saved_off_this_pc(self):
        self.assertEqual(auto_backup.run(self.client), {"status": "not_set_up"})
        backup_key.make(PASS, PASS)
        self.assertEqual(auto_backup.run(self.client), {"status": "not_set_up"})
        self.assertEqual(self.archives(), [])
        self.assertIn("locked copy", backup_key.status()["auto"]["error"])

    def test_a_running_app_is_backed_up_encrypted_and_restores_with_every_persons_rows(self):
        self.ready()
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as app:  # ALFRED still has its database open
            app.execute("PRAGMA journal_mode=WAL")
            result = auto_backup.run(self.client)
        self.assertEqual(result["status"], "saved")
        stored = self.wire.objects[cloud_backup.PREFIX + result["archive_sha256"] + ".zip"]
        for secret in (b"synthetic owned evidence", b"123.45", b"alice", b"not-a-real-credential", b"ledger"):
            self.assertNotIn(secret, stored)
        (folder,) = list(auto_backup.nightly_folder().iterdir())
        self.assertFalse((folder / "independent-local-restore").exists())  # no plain copy is left behind
        self.assertFalse(any(p.name.startswith("capture-") for p in folder.iterdir()))
        restored = self.root / "drill"
        cloud_backup.download(result["archive_sha256"], backup_key.key_path(), self.root / "downloaded", client=self.client)
        self.assertEqual(recovery.restore(self.root / "downloaded", backup_key.key_path(), restored)["financial_reconciliation"], "PASS")
        self.assertEqual(recovery.database_snapshot(restored / "db.sqlite3"), recovery.database_snapshot(self.runtime / "db.sqlite3"))
        auto = backup_key.status()["auto"]
        self.assertEqual((auto["kept"], auto["error"]), (1, ""))

    def test_seven_are_kept_in_r2_one_on_this_pc_and_hand_uploads_are_never_touched(self):
        self.ready()
        manual = cloud_backup.PREFIX + "f" * 64 + ".zip"
        self.wire.objects[manual] = b"an archive the owner uploaded by hand"
        with patch.object(auto_backup, "datetime", Clock()):
            digests = [auto_backup.run(self.client)["archive_sha256"] for _ in range(9)]
        self.assertEqual(self.archives(), sorted([manual] + [cloud_backup.PREFIX + d + ".zip" for d in digests[-7:]]))
        self.assertEqual(len(list(auto_backup.nightly_folder().iterdir())), 1)
        self.assertEqual(backup_key.status()["auto"]["kept"], 7)

    def test_a_failed_night_keeps_the_last_good_backup_and_says_so(self):
        self.ready()
        with patch.object(auto_backup, "datetime", Clock()):
            first = auto_backup.run(self.client)["archive_sha256"]
            self.wire.fail_part = 1
            with self.assertRaises(SyncUnavailable):
                auto_backup.run(self.client)
        self.assertEqual(self.archives(), [cloud_backup.PREFIX + first + ".zip"])
        self.assertEqual(len(list(auto_backup.nightly_folder().iterdir())), 1)  # the failed night's folder is removed
        auto = backup_key.status()["auto"]
        self.assertTrue(auto["last_ok"] and "tries again" in auto["error"])
        self.assertNotIn(str(self.root), auto["error"])

    def stored(self):
        return sum(map(len, self.wire.objects.values())) + sum(len(p) for upload in self.wire.uploads.values() for p in upload.values())

    def watch_peak(self):
        """The most the bucket ever held, checked after every request, unfinished parts included."""
        inner, self.peak = self.wire.request, 0
        def request(*args, **kwargs):
            try:
                return inner(*args, **kwargs)
            finally:
                self.peak = max(self.peak, self.stored())
        self.enterContext(patch("apps.ml_engine.services.memory_r2.request", request))

    def test_the_bucket_never_holds_more_than_the_free_storage_even_while_uploading(self):
        self.ready()
        size = len(self.wire.objects[cloud_backup.PREFIX + auto_backup.run(self.client)["archive_sha256"] + ".zip"])
        manual = cloud_backup.PREFIX + "f" * 64 + ".zip"
        self.wire.objects[manual] = b"h" * (size // 2)  # a hand upload counts against the free storage too
        limit = self.stored() + 2 * size + size // 4  # room for about three nightly copies beside the hand upload
        self.enterContext(patch.object(cloud_backup, "FREE_STORAGE", limit))
        self.watch_peak()
        with patch.object(auto_backup, "datetime", Clock()):
            digests = [auto_backup.run(self.client)["archive_sha256"] for _ in range(5)]
        self.assertLessEqual(self.peak, limit)
        self.assertIn(manual, self.wire.objects)  # never touched
        self.assertIn(cloud_backup.PREFIX + digests[-1] + ".zip", self.wire.objects)
        self.assertEqual(backup_key.status()["auto"]["error"], "")

    def test_a_backup_that_cannot_fit_is_not_uploaded_and_the_last_good_one_stays(self):
        self.ready()
        first = auto_backup.run(self.client)["archive_sha256"]
        self.enterContext(patch.object(cloud_backup, "FREE_STORAGE", self.stored() + 100))
        with patch.object(auto_backup, "datetime", Clock()), self.assertRaises(cloud_backup.GateError):
            auto_backup.run(self.client)
        self.assertEqual(self.archives(), [cloud_backup.PREFIX + first + ".zip"])
        auto = backup_key.status()["auto"]
        self.assertIn("past its free 9 GB", auto["error"])
        self.assertEqual(auto_backup.status()["tries"]["count"], 1)  # a refusal before any part went up is not a try

    def test_a_cut_off_upload_is_cleared_and_a_running_one_waits(self):
        self.ready()
        name = cloud_backup.PREFIX + "a" * 64 + ".zip"
        self.wire.uploads["cut-off"] = {1: b"x" * 500}
        self.wire.started["cut-off"] = (name, "2026-01-01T00:00:00.000Z")
        self.assertEqual(auto_backup.run(self.client)["status"], "saved")
        self.assertNotIn("cut-off", self.wire.uploads)
        self.wire.uploads["running"] = {1: b"x" * 500}
        self.wire.started["running"] = (name, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        with patch.object(auto_backup, "datetime", Clock()), self.assertRaises(cloud_backup.GateError):
            auto_backup.run(self.client)
        self.assertIn("running", self.wire.uploads)
        self.assertIn("still running", backup_key.status()["auto"]["error"])

    def test_tries_stop_for_the_month_far_below_the_free_million_writes(self):
        largest_try = cloud_backup.FREE_STORAGE // (8 * 1024 * 1024) + 20  # parts at the real 8 MiB size, plus the other calls
        self.assertLess(auto_backup.MONTHLY_TRIES * largest_try, 100_000)
        self.ready()
        auto_backup._record(tries={"month": datetime.now(timezone.utc).strftime("%Y-%m"), "count": auto_backup.MONTHLY_TRIES})
        self.assertEqual(auto_backup.run(self.client), {"status": "monthly_limit"})
        self.assertEqual(self.archives(), [])
        self.assertIn("next month", backup_key.status()["auto"]["error"])

    def test_the_backup_folder_sits_beside_the_data_folder(self):
        self.assertEqual(auto_backup.nightly_folder(), self.root / "runtime-backups" / "nightly")


class PortableRestoreTests(R2Setup):
    """A new PC or Windows account must open the restored chats, memories and service keys (owner 2026-11-26)."""

    def test_windows_bound_vault_keys_travel_inside_the_archive_and_are_resealed_on_restore(self):
        from cryptography.fernet import Fernet
        from apps.ml_engine.services.memory_key import protect_key
        vault = self.runtime / "artifacts/private-memory-v2"; vault.mkdir(parents=True)
        raw = Fernet.generate_key()
        (vault / "journal.key").write_bytes(b"M15DPAPI1" + bytes(1) + protect_key(raw))
        (vault / "sync-owner.key").write_bytes(b"M15SYNC1" + bytes(1) + b"another user's sealed key")
        (self.runtime / "artifacts/personal-keys").mkdir(parents=True)
        (self.runtime / "artifacts/personal-keys/user-1.json").write_text('{"TRAVEL_GOOGLE_MAPS_API_KEY": "sealed-synthetic"}')
        self.assertEqual(recovery.portable_key(vault / "journal.key"), recovery.PORTABLE + b"M15DPAPI1" + bytes(1) + raw)
        self.assertIsNone(recovery.portable_key(vault / "sync-owner.key"))  # not this user's: left sealed
        key = self.root / "portable.key"; key.write_bytes(Fernet.generate_key())
        recovery.create(self.runtime, self.root / "backup", key, "synthetic-portable", "a" * 40, "b" * 40)
        archive = (self.root / "backup/recovery.zip").read_bytes()
        self.assertNotIn(raw, archive)  # unsealed only inside the encryption
        restored = self.root / "restored"
        self.assertEqual(recovery.restore(self.root / "backup", key, restored)["LOCAL_BACKUP_VERIFIED"], "PASS")
        blob = (restored / "artifacts/private-memory-v2/journal.key").read_bytes()
        self.assertTrue(blob.startswith(b"M15DPAPI1" + bytes(1)))
        self.assertEqual(protect_key(blob[10:], decrypt=True), raw)
        self.assertEqual((restored / "artifacts/private-memory-v2/sync-owner.key").read_bytes(),
                         (vault / "sync-owner.key").read_bytes())
        self.assertTrue((restored / "artifacts/personal-keys/user-1.json").is_file())


class ConnectCloudTests(R2Setup):
    VALUES = {"account_id": PROFILE["account_id"], "bucket": PROFILE["bucket"], "access_key": PROFILE["access_key"],
              "secret_key": PROFILE["secret_key"]}

    def env(self):
        path = self.runtime / "config/local.env"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def test_values_are_checked_with_cloudflare_before_they_are_saved(self):
        before = self.env()
        with override_settings(ALFRED_CLOUD_BACKUP_AUTHORIZED=False, ALFRED_MEMORY_R2_ACCOUNT_ID=""):
            self.assertFalse(backup_key.status()["cloud"]["on"])
            for bad in ({**self.VALUES, "account_id": "not-hex"}, {**self.VALUES, "secret_key": "has'quote" * 5}, {"bucket": "x"}, "text"):
                with self.assertRaises(backup_key.BackupKeyError):
                    auto_backup.connect(bad)
            with patch("apps.ml_engine.services.memory_r2.request", side_effect=PublicHTTPError("authorization_failed")), \
                    self.assertRaisesRegex(backup_key.BackupKeyError, "did not accept"):
                auto_backup.connect(self.VALUES)
            self.assertEqual(self.env(), before)
            with patch.dict(os.environ):
                auto_backup.connect(self.VALUES)
                cloud = backup_key.status()
                self.assertEqual(cloud["cloud"], {"on": True, "bucket": PROFILE["bucket"]})
                self.assertNotIn(PROFILE["secret_key"], json.dumps(cloud))
                self.assertIn("ALFRED_CLOUD_BACKUP_AUTHORIZED='true'", self.env())
                self.assertIn("SYNTHETIC_ONLY=not-a-real-credential", self.env())  # other lines kept
                auto_backup.turn_off()
                self.assertFalse(backup_key.status()["cloud"]["on"])
                self.assertIn(PROFILE["access_key"], self.env())  # the bucket stays connected for fetching the key copy


class BackupSettingsTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-auto-backup-ui-synthetic-")))
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root)}))
        self.owner = get_user_model().objects.create_user("synthetic-backup-owner", is_superuser=True)
        self.client = Client()
        self.client.force_login(self.owner)

    def post(self, action):
        return self.client.post("/api/settings/backup-key/", json.dumps({"action": action}), content_type="application/json")

    def test_save_fetch_and_back_up_now_go_through_the_settings_api(self):
        with patch.object(backup_key, "save_to_r2") as save, patch.object(backup_key, "fetch_from_r2") as fetch, \
                patch.object(auto_backup.backup_now, "delay") as now:
            for action in ("save_r2", "fetch_r2", "backup_now"):
                self.assertEqual(self.post(action).status_code, 200)
        save.assert_called_once_with(); fetch.assert_called_once_with(); now.assert_called_once_with()
        self.assertEqual(self.post("something_else").status_code, 400)
        self.assertIn('id="backupNow"', self.client.get("/settings/").content.decode())
