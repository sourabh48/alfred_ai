"""Encrypted recovery uses disposable synthetic databases and newly generated test keys only."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile
from types import SimpleNamespace

from cryptography.fernet import Fernet, InvalidToken
from alfred_private_storage import private_directory
from scripts import release_gate as release
from scripts import release_recovery as recovery


class ReleaseRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="alfred-recovery-synthetic-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "runtime"
        private_directory(self.runtime)
        (self.runtime / "config").mkdir()
        (self.runtime / "media").mkdir()
        (self.runtime / "config/native.env").write_text("SYNTHETIC_ONLY=not-a-real-credential")
        (self.runtime / "media/synthetic.txt").write_text("synthetic owned evidence")
        (self.runtime / "artifacts/native").mkdir(parents=True)
        for name in ("db.sqlite3", "artifacts/native/jobs.sqlite3"):
            with closing(sqlite3.connect(self.runtime / name)) as db, db:
                db.execute("CREATE TABLE owner (id INTEGER PRIMARY KEY)")
                db.execute("INSERT INTO owner VALUES (1)")
                db.execute("CREATE TABLE ledger (id INTEGER PRIMARY KEY, owner_id INTEGER REFERENCES owner(id), amount NUMERIC, fingerprint TEXT, sharing INTEGER)")
                db.execute("INSERT INTO ledger VALUES (1,1,'123.45','synthetic-fingerprint',0)")
        memory = self.runtime / "artifacts/private-memory-v2"
        memory.mkdir()
        with closing(sqlite3.connect(memory / "verified.sqlite3")) as db, db:
            db.execute("CREATE TABLE encrypted_memory (record BLOB)")
            db.execute("INSERT INTO encrypted_memory VALUES (?)", (b"synthetic-encrypted-blob",))
        self.key = self.root / "test-only.key"
        self.key.write_bytes(Fernet.generate_key())
        self.backup = self.root / "backup"

    def create(self):
        return recovery.create(self.runtime, self.backup, self.key, "synthetic-release", "a" * 40, "b" * 40)

    def test_authenticated_independent_local_restore_preserves_data_but_proves_no_device_loss(self):
        receipt = self.create()
        self.assertEqual(receipt["LOCAL_BACKUP_VERIFIED"], "PASS")
        self.assertEqual(receipt["database_count"], 3)
        for name in ("OFF_DEVICE_COPY_VERIFIED", "PORTABLE_KEY_VERIFIED", "INDEPENDENT_DEVICE_LOSS_RESTORE_VERIFIED"):
            self.assertEqual(receipt[name], "NOT_RUN")
        self.assertNotIn("123.45", json.dumps(receipt))
        self.assertNotIn("synthetic-fingerprint", json.dumps(receipt))
        self.assertNotIn(b"synthetic owned evidence", (self.backup / "recovery.zip").read_bytes())
        restored = self.backup / "independent-local-restore"
        self.assertEqual(recovery.database_snapshot(self.runtime / "db.sqlite3"), recovery.database_snapshot(restored / "db.sqlite3"))
        self.assertEqual((restored / "config/native.env").read_bytes(), (self.runtime / "config/native.env").read_bytes())

    def test_committed_wal_rows_are_included_without_copying_raw_sidecars(self):
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("INSERT INTO ledger VALUES (2,1,'20.05','synthetic-transfer-leg',0)")
            db.commit()
            self.assertTrue(Path(str(self.runtime / "db.sqlite3") + "-wal").exists())
            receipt = self.create()
            self.assertEqual(receipt["LOCAL_BACKUP_VERIFIED"], "PASS")
            restored = self.backup / "independent-local-restore/db.sqlite3"
            self.assertEqual(recovery.database_snapshot(restored)["ledger"]["count"], 2)
            metadata = json.loads((self.backup / "independent-local-restore/manifest.json").read_text())
            self.assertFalse(any(r["backup_path"].endswith(("-wal", "-shm")) for r in metadata["files"]))

    def test_active_native_writer_blocks_without_stopping_any_process(self):
        with recovery.InstanceLock(self.runtime):
            with self.assertRaisesRegex(release.GateError, "native_writer_running"):
                self.create()
        self.assertFalse((self.backup / "recovery.zip").exists())

    def test_active_worker_blocks_even_without_a_supervisor_or_state_file(self):
        with recovery.InstanceLock(self.runtime, "worker.lock"):
            with self.assertRaisesRegex(release.GateError, "native_writer_running"):
                self.create()
        self.assertFalse((self.backup / "recovery.zip").exists())

    def test_stopped_runtime_with_live_reused_pids_does_not_block_local_recovery(self):
        (self.runtime / "artifacts/native/runtime.json").write_text(json.dumps({
            "status": "stopped", "pid": os.getpid(), "worker_pid": os.getpid(),
        }))
        receipt = self.create()
        self.assertEqual(receipt["LOCAL_BACKUP_VERIFIED"], "PASS")
        restored = self.backup / "independent-local-restore/db.sqlite3"
        self.assertEqual(recovery.database_snapshot(self.runtime / "db.sqlite3"), recovery.database_snapshot(restored))

    def test_backup_barriers_block_new_native_processes_throughout_capture(self):
        with recovery.writer_barriers(self.runtime, [self.runtime / "db.sqlite3"]):
            for name in ("instance.lock", "worker.lock"):
                with self.subTest(lock=name), self.assertRaises(OSError):
                    with recovery.InstanceLock(self.runtime, name):
                        self.fail("A native process entered during backup capture")

    def test_active_sqlite_writer_blocks(self):
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db:
            db.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(release.GateError, "sqlite_writer_busy"):
                self.create()
        self.assertFalse((self.backup / "recovery.zip").exists())

    def test_corrupt_or_missing_archive_is_not_recovery_success(self):
        self.create()
        archive = self.backup / "recovery.zip"
        archive.write_bytes(archive.read_bytes() + b"corrupt synthetic trailer")
        with self.assertRaisesRegex(release.GateError, "backup_archive_hash_failed"):
            recovery.restore(self.backup, self.key, self.root / "corrupt")
        archive.rename(self.backup / "preserved-corrupt.zip")
        with self.assertRaises(FileNotFoundError):
            recovery.restore(self.backup, self.key, self.root / "missing")

    def test_missing_or_wrong_key_does_not_create_a_plaintext_restore(self):
        self.create()
        with self.assertRaises(FileNotFoundError):
            recovery.restore(self.backup, self.root / "absent.key", self.root / "no-key")
        wrong = self.root / "wrong-test-only.key"
        wrong.write_bytes(Fernet.generate_key())
        with self.assertRaises(InvalidToken):
            recovery.restore(self.backup, wrong, self.root / "wrong-key")
        self.assertFalse((self.root / "wrong-key").exists())

    def test_new_backup_never_overwrites_an_old_verified_backup(self):
        self.create()
        old_hash = release.sha256(self.backup / "recovery.zip")
        with self.assertRaisesRegex(release.GateError, "recovery_destination_must_be_new"):
            self.create()
        self.assertEqual(release.sha256(self.backup / "recovery.zip"), old_hash)

    def test_missing_required_coverage_blocks(self):
        (self.runtime / "artifacts/native/jobs.sqlite3").rename(self.runtime / "artifacts/native/retained.sqlite3")
        with self.assertRaisesRegex(release.GateError, "required_recovery_coverage_missing"):
            self.create()

    def test_foreign_key_failure_and_financial_difference_are_visible_without_values(self):
        before = recovery.database_snapshot(self.runtime / "db.sqlite3")
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db, db:
            db.execute("UPDATE ledger SET amount='123.46'")
        self.assertNotEqual(before, recovery.database_snapshot(self.runtime / "db.sqlite3"))
        with closing(sqlite3.connect(self.runtime / "db.sqlite3")) as db, db:
            db.execute("UPDATE ledger SET owner_id=999")
        with self.assertRaisesRegex(release.GateError, "sqlite_foreign_key_failed"):
            recovery.database_snapshot(self.runtime / "db.sqlite3")

    def test_restore_rejects_an_authenticated_traversal_manifest(self):
        self.create()
        cipher, _ = recovery.cipher_from_file(self.key)
        archive = self.backup / "recovery.zip"
        with zipfile.ZipFile(archive) as zipped:
            entries = {name: zipped.read(name) for name in zipped.namelist()}
        metadata = json.loads(cipher.decrypt(entries["manifest.fernet"]))
        metadata["files"][0]["backup_path"] = "../outside.sqlite3"
        entries["manifest.fernet"] = cipher.encrypt(json.dumps(metadata).encode())
        with zipfile.ZipFile(archive, "w") as zipped:
            for name, content in entries.items():
                zipped.writestr(name, content)
        public = json.loads((self.backup / "backup.json").read_text())
        public.update(archive_bytes=archive.stat().st_size, archive_sha256=release.sha256(archive))
        (self.backup / "backup.json").write_text(json.dumps(public))
        with self.assertRaisesRegex(release.GateError, "unsafe_restore_manifest_path"):
            recovery.restore(self.backup, self.key, self.root / "traversal")
        self.assertFalse((self.root / "outside.sqlite3").exists())

    def test_failed_independent_restore_preserves_new_evidence(self):
        original = subprocess.run
        def fail_restore(command, *args, **kwargs):
            if any(str(part).endswith("release_recovery.py") for part in command):
                return subprocess.CompletedProcess(command, 1, b"", b"synthetic-secret")
            return original(command, *args, **kwargs)
        with patch.object(recovery.subprocess, "run", side_effect=fail_restore):
            with self.assertRaisesRegex(release.GateError, "independent_local_restore_failed"):
                self.create()
        self.assertTrue((self.backup / "recovery.zip").exists())
        self.assertTrue(any(self.backup.glob("capture-*")))

    def test_rejected_or_interrupted_restore_never_publishes_a_runtime(self):
        self.create()
        for failure in (release.GateError("synthetic_validation_failure"), KeyboardInterrupt()):
            destination = self.root / ("interrupted" if isinstance(failure, KeyboardInterrupt) else "rejected")
            with self.subTest(failure=type(failure).__name__):
                with patch.object(recovery, "verify", side_effect=failure):
                    with self.assertRaises(type(failure)):
                        recovery.restore(self.backup, self.key, destination)
                self.assertFalse(destination.exists(), "An incomplete recovery must never be a launchable runtime")
                retained = list(self.root.glob(destination.name + ".restore-incomplete-*"))
                self.assertEqual(len(retained), 1)
                self.assertEqual(recovery.database_snapshot(retained[0] / "db.sqlite3"),
                                 recovery.database_snapshot(self.runtime / "db.sqlite3"))
                # A fresh attempt never merges with the interrupted extraction.
                self.assertEqual(recovery.restore(self.backup, self.key, destination)["LOCAL_BACKUP_VERIFIED"], "PASS")
                self.assertTrue(retained[0].is_dir())

    def test_restore_never_overwrites_an_existing_or_concurrently_created_destination(self):
        self.create()
        destination = self.root / "existing"
        destination.mkdir()
        retained = destination / "retained.txt"
        retained.write_bytes(b"newer data must survive")
        with self.assertRaisesRegex(release.GateError, "recovery_destination_must_be_new"):
            recovery.restore(self.backup, self.key, destination)
        original_verify = recovery.verify
        concurrent = self.root / "concurrent"
        def verify_and_create(*args, **kwargs):
            result = original_verify(*args, **kwargs)
            concurrent.mkdir()
            (concurrent / "retained.txt").write_bytes(retained.read_bytes())
            return result
        with patch.object(recovery, "verify", side_effect=verify_and_create):
            with self.assertRaisesRegex(release.GateError, "recovery_destination_must_be_new"):
                recovery.restore(self.backup, self.key, concurrent)
        self.assertEqual(retained.read_bytes(), b"newer data must survive")
        self.assertEqual((concurrent / "retained.txt").read_bytes(), retained.read_bytes())

    def test_failed_financial_reconciliation_never_publishes_and_retry_is_fresh(self):
        self.create()
        destination = self.root / "reconciliation-rejected"
        with patch.object(recovery, "database_snapshot", return_value={}):
            with self.assertRaisesRegex(release.GateError, "financial_restore_reconciliation_failed"):
                recovery.restore(self.backup, self.key, destination)
        self.assertFalse(destination.exists())
        retained = list(self.root.glob(destination.name + ".restore-incomplete-*"))
        self.assertEqual(len(retained), 1)
        self.assertEqual(recovery.restore(self.backup, self.key, destination)["LOCAL_BACKUP_VERIFIED"], "PASS")
        self.assertTrue(retained[0].is_dir())


class RestorePublicationTests(unittest.TestCase):
    def test_verified_tree_is_published_once(self):
        with TemporaryDirectory() as temporary:
            staging, destination = Path(temporary) / "staging", Path(temporary) / "final"
            staging.mkdir()
            (staging / "verified.txt").write_bytes(b"synthetic verified tree")
            recovery.publish_restore(staging, destination)
            self.assertFalse(staging.exists())
            self.assertEqual((destination / "verified.txt").read_bytes(), b"synthetic verified tree")

    def test_even_an_empty_concurrent_destination_is_never_replaced(self):
        with TemporaryDirectory() as temporary:
            staging, destination = Path(temporary) / "staging", Path(temporary) / "final"
            staging.mkdir(); destination.mkdir()
            (staging / "verified.txt").write_bytes(b"synthetic verified tree")
            with self.assertRaisesRegex(release.GateError, "recovery_destination_must_be_new"):
                recovery.publish_restore(staging, destination)
            self.assertTrue(staging.is_dir())
            self.assertEqual(list(destination.iterdir()), [])

    def test_unsupported_atomic_publication_retains_staging(self):
        with TemporaryDirectory() as temporary:
            staging, destination = Path(temporary) / "staging", Path(temporary) / "final"
            staging.mkdir()
            with patch.object(recovery.os, "name", "posix"), patch("ctypes.CDLL", return_value=SimpleNamespace()):
                with self.assertRaisesRegex(release.GateError, "atomic_restore_publication_unavailable"):
                    recovery.publish_restore(staging, destination)
            self.assertTrue(staging.is_dir())
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
