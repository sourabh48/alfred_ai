"""Real Windows permission checks against disposable synthetic storage only."""
import copy
from contextlib import closing, redirect_stdout
import ctypes
from ctypes import wintypes
import os
import json
import hashlib
from io import StringIO
from pathlib import Path
import sqlite3
import subprocess
from tempfile import TemporaryDirectory
import time
from unittest import TestCase, skipUnless
from unittest.mock import patch
from types import SimpleNamespace

from alfred_private_storage import (
    PrivateStorageUnavailable, acl_snapshot, apply_plan, current_sid, guard_sqlite_storage,
    inspect_storage, network_drive, permission_plan, private_directory, replace_acl, rollback_plan,
    safe_path, verify_private, main,
)


@skipUnless(os.name == "nt", "Windows access-control acceptance requires Windows")
class PrivateStorageTests(TestCase):
    def test_fresh_runtime_and_children_are_owner_system_only(self):
        with TemporaryDirectory() as directory:
            root = private_directory(Path(directory))
            for name in ("config", "media", "models", "cache", "artifacts/native"):
                folder = private_directory(root / name)
                sample = folder / "synthetic.bin"
                sample.write_bytes(b"synthetic private fixture")
                self.assertTrue(verify_private(folder))
                self.assertTrue(verify_private(sample))
                self.assertEqual(sample.read_bytes(), b"synthetic private fixture")
                self.assertEqual({e["sid"] for e in acl_snapshot(sample)["entries"]},
                                 {current_sid(), "S-1-5-18"})

    def test_restricted_windows_identity_cannot_read_private_file(self):
        # A restricting SID must independently pass the Windows access check.
        with TemporaryDirectory() as directory:
            root = private_directory(Path(directory))
            sample = root / "synthetic.db"
            sample.write_bytes(b"synthetic private fixture")
            api = ctypes.WinDLL("advapi32", use_last_error=True)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            pointer = ctypes.c_void_p
            class SidAndAttributes(ctypes.Structure):
                _fields_ = [("sid", pointer), ("attributes", wintypes.DWORD)]
            api.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
            api.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(pointer)]
            api.CreateRestrictedToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, pointer,
                wintypes.DWORD, pointer, wintypes.DWORD, ctypes.POINTER(SidAndAttributes), ctypes.POINTER(wintypes.HANDLE)]
            api.ImpersonateLoggedOnUser.argtypes = [wintypes.HANDLE]
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, pointer,
                                          wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.LocalFree.argtypes = [pointer]
            token, restricted, sid = wintypes.HANDLE(), wintypes.HANDLE(), pointer()
            impersonating = False
            try:
                self.assertTrue(api.OpenProcessToken(kernel.GetCurrentProcess(), 14, ctypes.byref(token)))
                self.assertTrue(api.ConvertStringSidToSidW("S-1-5-32-545", ctypes.byref(sid)))
                restricting = SidAndAttributes(sid, 0)
                self.assertTrue(api.CreateRestrictedToken(token, 1, 0, None, 0, None, 1,
                                                         ctypes.byref(restricting), ctypes.byref(restricted)))
                self.assertTrue(api.ImpersonateLoggedOnUser(restricted))
                impersonating = True
                handle = kernel.CreateFileW(str(sample), 0x80000000, 7, None, 3, 128, None)
                error = ctypes.get_last_error()
                if handle != wintypes.HANDLE(-1).value:
                    kernel.CloseHandle(handle)
                self.assertEqual(handle, wintypes.HANDLE(-1).value)
                self.assertEqual(error, 5)
            finally:
                if impersonating:
                    self.assertTrue(api.RevertToSelf())
                for handle in (restricted, token):
                    if handle.value:
                        kernel.CloseHandle(handle)
                if sid.value:
                    kernel.LocalFree(sid)
            self.assertEqual(sample.read_bytes(), b"synthetic private fixture")

    def unsafe_tree(self, root):
        replace_acl(root, f"D:P(A;OICI;FA;;;{current_sid()})(A;OICI;FA;;;SY)(A;OICI;FR;;;AU)(A;OICI;FR;;;BU)")
        child = root / "config"
        child.mkdir()
        (child / "key.fixture").write_bytes(b"synthetic retained key")
        return child

    def test_existing_unsafe_data_fails_without_mutating_permissions(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            child = self.unsafe_tree(root)
            before = permission_plan(root)
            for folder in (root, child):
                with self.assertRaises(PrivateStorageUnavailable):
                    private_directory(folder)
            self.assertEqual(permission_plan(root), before)
            self.assertEqual((child / "key.fixture").read_bytes(), b"synthetic retained key")

    def test_restored_children_inherit_only_from_a_verified_private_parent(self):
        with TemporaryDirectory() as directory:
            root = private_directory(Path(directory))
            child = root / "restored/config"
            child.mkdir(parents=True)
            (child / "key.fixture").write_bytes(b"synthetic recovery key")
            before = acl_snapshot(child)
            self.assertTrue(verify_private(child))
            self.assertEqual(private_directory(child), child)
            self.assertEqual(acl_snapshot(child), before)

    def test_authorized_quiesced_repair_and_permission_rollback(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            child = self.unsafe_tree(root)
            plan = permission_plan(root)
            apply_plan(plan, authorization_reference="synthetic-owner-approval", quiesced=True)
            self.assertTrue(all(verify_private(p) for p in (root, child, child / "key.fixture")))
            self.assertEqual((child / "key.fixture").read_bytes(), b"synthetic retained key")
            rollback_plan(plan, authorization_reference="synthetic-rollback-approval", quiesced=True)
            self.assertEqual(permission_plan(root), plan)

    def test_missing_approval_changed_plan_or_active_writers_block_before_mutation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.unsafe_tree(root)
            plan = permission_plan(root)
            for action in (apply_plan, rollback_plan):
                for approval, stopped in ((None, True), ("synthetic", False)):
                    with self.assertRaises(PrivateStorageUnavailable):
                        action(plan, authorization_reference=approval, quiesced=stopped)
                    self.assertEqual(permission_plan(root), plan)
            changed = copy.deepcopy(plan)
            changed["records"][-1]["bytes"] += 1
            with self.assertRaises(PrivateStorageUnavailable):
                apply_plan(changed, authorization_reference="synthetic", quiesced=True)
            self.assertEqual(permission_plan(root), plan)

    def test_file_changes_block_blind_permission_rollback(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            child = self.unsafe_tree(root)
            plan = permission_plan(root)
            apply_plan(plan, authorization_reference="synthetic", quiesced=True)
            (child / "key.fixture").write_bytes(b"new synthetic value")
            with self.assertRaises(PrivateStorageUnavailable):
                rollback_plan(plan, authorization_reference="synthetic", quiesced=True)
            self.assertTrue(verify_private(root))
            self.assertEqual((child / "key.fixture").read_bytes(), b"new synthetic value")

    def test_repair_cli_is_dry_run_and_requires_pinned_plan_and_explicit_approval(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "synthetic-runtime"
            root.mkdir()
            self.unsafe_tree(root)
            before = permission_plan(root)
            retained = base / "plans/permissions.json"
            def command(*args):
                with patch("sys.argv", ["alfred_private_storage.py", str(root), *args]), redirect_stdout(StringIO()) as output:
                    result = main()
                return result, json.loads(output.getvalue())
            code, report = command("--plan", str(retained))
            self.assertEqual((code, report["status"]), (0, "DRY_RUN"))
            self.assertEqual(permission_plan(root), before)
            self.assertTrue(verify_private(retained))
            digest = hashlib.sha256(retained.read_bytes()).hexdigest()
            for value in ("0" * 64, digest):
                code, report = command("--plan", str(retained), "--apply", "--expected-sha256", value)
                self.assertEqual((code, report["status"]), (1, "BLOCKED"))
                self.assertEqual(permission_plan(root), before)
            code, report = command("--plan", str(retained), "--apply", "--expected-sha256", digest,
                                   "--authorization-reference", "synthetic-approved", "--quiesced")
            self.assertEqual((code, report["status"]), (0, "APPLIED"))
            self.assertTrue(verify_private(root))
            self.assertEqual(json.loads(retained.read_text()), before)

    def test_expired_deadline_linked_paths_and_permission_failures_are_closed(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fresh"
            with self.assertRaises(PrivateStorageUnavailable):
                private_directory(path, deadline=time.monotonic() - 1)
            self.assertFalse(path.exists())
            with patch.object(Path, "is_junction", return_value=True):
                with self.assertRaises(PrivateStorageUnavailable):
                    private_directory(path)
            self.assertFalse(path.exists())
            with patch("alfred_private_storage.replace_acl", side_effect=PrivateStorageUnavailable("synthetic denial")):
                with self.assertRaises(PrivateStorageUnavailable):
                    private_directory(path)
            self.assertFalse(any(path.iterdir()))

    def test_native_runtime_rejects_unsafe_root_before_creating_secrets(self):
        from alfred_native import configure, runtime_directory
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            self.unsafe_tree(root)
            before = permission_plan(root)
            for action in (configure, runtime_directory):
                with self.assertRaises(PrivateStorageUnavailable):
                    action(root)
            self.assertEqual(permission_plan(root), before)
            self.assertFalse((root / "config/native.env").exists())

    def test_loosened_signing_key_is_refused_without_changing_it(self):
        from alfred_ai.local_config import native_secret_file
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = private_directory(Path(directory))
            secret = native_secret_file(root)
            self.assertTrue(verify_private(secret))
            content = secret.read_bytes()
            self.assertEqual(native_secret_file(root), secret)
            replace_acl(secret, f"D:P(A;;FA;;;{current_sid()})(A;;FA;;;SY)(A;;FR;;;AU)")
            before = acl_snapshot(secret)
            with self.assertRaises(PermissionError):
                native_secret_file(root)
            self.assertEqual(acl_snapshot(secret), before)
            self.assertEqual(secret.read_bytes(), content)

    def test_loosened_sqlite_side_file_is_refused_and_a_private_one_accepted(self):
        with TemporaryDirectory() as directory:
            root = private_directory(Path(directory))
            database = root / "synthetic.sqlite3"
            config = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": database}}
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("CREATE TABLE synthetic(id INTEGER)")
                # SQLite's own side files inherit the private folder.
                self.assertTrue(database.with_name(database.name + "-wal").exists())
                guard_sqlite_storage(config)
            for suffix in ("-wal", "-shm", "-journal"):
                side = database.with_name(database.name + suffix)
                side.write_bytes(b"synthetic recent rows")
                replace_acl(side, f"D:P(A;;FA;;;{current_sid()})(A;;FA;;;SY)(A;;FR;;;AU)")
                before = acl_snapshot(side)
                with self.subTest(suffix=suffix), self.assertRaises(PrivateStorageUnavailable):
                    guard_sqlite_storage(config)
                self.assertEqual(acl_snapshot(side), before)
                side.unlink()
            guard_sqlite_storage(config)

    def test_mapped_network_drive_is_refused_before_anything_is_created(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "fresh"
            self.assertFalse(network_drive(target))
            remote = {"GetDriveTypeW": lambda anchor: 4}
            with patch("alfred_private_storage.windows", return_value=(None, SimpleNamespace(**remote))):
                self.assertTrue(network_drive(target))
                with self.assertRaises(PrivateStorageUnavailable):
                    safe_path(target)
            with patch("alfred_private_storage.network_drive", return_value=True):
                with self.assertRaises(PrivateStorageUnavailable):
                    private_directory(target)
            self.assertFalse(target.exists())

    def test_inspection_reports_permissions_without_changing_or_naming_private_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.unsafe_tree(root)
            (root / "config/native.env").write_bytes(b"synthetic signing key")
            (root / "synthetic-private-statement.pdf").write_bytes(b"synthetic")
            outside = private_directory(root.parent / (root.name + "-outside"))
            self.addCleanup(outside.rmdir)
            subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "linked"), str(outside)], check=True, capture_output=True)
            before = {path: (path.stat().st_mtime_ns, acl_snapshot(path)) for path in root.rglob("*") if path.name != "linked"}
            with patch("sys.argv", ["alfred_private_storage.py", str(root), "--inspect"]), redirect_stdout(StringIO()) as output:
                self.assertEqual(main(), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["status"], "NEEDS_REPAIR")
            self.assertEqual(report["sensitive"]["config/native.env"], "loose")
            self.assertEqual(report["sensitive"]["db.sqlite3"], "absent")
            self.assertEqual(report["counts"]["linked"], 1)
            self.assertEqual(report["counts"]["private"], 0)
            self.assertIn("S-1-5-11", report["outside_access_sids"])
            self.assertNotIn("synthetic-private-statement", output.getvalue())
            self.assertNotIn("key.fixture", output.getvalue())
            self.assertEqual({path: (path.stat().st_mtime_ns, acl_snapshot(path)) for path in root.rglob("*") if path.name != "linked"}, before)
            with patch("sys.argv", ["alfred_private_storage.py", str(root), "--inspect", "--apply"]), redirect_stdout(StringIO()) as output:
                self.assertEqual(main(), 1)
            private = private_directory(root.parent / (root.name + "-private"))
            self.addCleanup(private.rmdir)
            self.assertEqual(inspect_storage(private)["status"], "PRIVATE")

    def test_parser_and_ocr_temporary_data_are_private_before_worker_access(self):
        from alfred_ai.services import bounded_parser, document_extraction
        from apps.expenses.services import statement_import
        paths = []
        def worker(command, **kwargs):
            target = Path(command[-1])
            self.assertTrue(verify_private(target))
            if target.is_dir():
                self.assertTrue(verify_private(target / "input"))
                (target / "output.json").write_text(json.dumps({"result": {"text": "synthetic"}}))
            paths.append(target)
            return SimpleNamespace(returncode=0, stdout=json.dumps({"text": "synthetic"}))
        with patch.object(bounded_parser, "ocr_command", side_effect=lambda kind, source, folder, limit: ["synthetic", folder]), \
             patch.object(bounded_parser.subprocess, "run", side_effect=worker):
            self.assertEqual(bounded_parser.run_bounded_parser("credit_metadata", b"synthetic", "fixture.pdf"),
                             {"text": "synthetic"})
        for module, function in ((document_extraction, document_extraction._extract_pdf_with_isolated_ocr),
                                 (statement_import, statement_import._extract_with_isolated_ocr)):
            with patch.object(module, "ocr_command", side_effect=lambda kind, source, path, limit: ["synthetic", path]), \
                 patch.object(module.subprocess, "run", side_effect=worker):
                result = function(b"synthetic" * 1024, page_limit=1)
                self.assertIn("synthetic", str(result))
        self.assertTrue(all(not p.exists() for p in paths))
