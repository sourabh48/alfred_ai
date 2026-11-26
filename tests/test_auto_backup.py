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
from urllib.parse import urlsplit

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
    """Adds plain object PUT, whole GET (404 when missing) and object DELETE to the signed multipart wire."""

    def request(self, method, url, *, headers, data=None, accepted_statuses=(200,), **kwargs):
        parts = urlsplit(url); key = parts.path.lstrip("/").partition("/")[2]
        outgoing = {k.lower(): v for k, v in headers.items()}
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

    def test_the_backup_folder_sits_beside_the_data_folder(self):
        self.assertEqual(auto_backup.nightly_folder(), self.root / "runtime-backups" / "nightly")


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
