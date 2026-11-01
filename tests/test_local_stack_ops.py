import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

from alfred_private_storage import verify_private
from scripts.local_stack_ops import (
    Compose, OperationError, SERVICES, backup, digest, inspect_archive, read_env_file, restore_check,
    ROOT, validate_restore_name, verify, write_json,
)


class LocalStackOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, name="media/synthetic-receipt.txt", link=False):
        path = self.root / "files.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            member = tarfile.TarInfo(name)
            if link:
                member.type = tarfile.SYMTYPE
                member.linkname = "../../outside"
                archive.addfile(member)
            else:
                payload = b"explicit synthetic fixture"
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
        return path

    def test_restore_database_name_rejects_live_targets_and_shell_characters(self):
        for name in ("alfred", "postgres", "alfred_restore_check_foo", "alfred_restore_check_" + "a" * 32 + ";whoami"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_restore_name(name)
        validate_restore_name("alfred_restore_check_" + "a" * 32)

    def test_archive_rejects_traversal_absolute_paths_and_links(self):
        for name in ("../outside", "/media/receipt", "media/../../outside", "config/local.env",
                     "media\\..\\outside", "media/file.txt:alternate-stream"):
            with self.subTest(name=name), self.assertRaises(OperationError):
                inspect_archive(self.archive(name))
        with self.assertRaises(OperationError):
            inspect_archive(self.archive(link=True))

    def test_archive_rejects_duplicate_normalized_paths(self):
        path = self.root / "duplicate.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name in ("media/receipt.txt", "media/./receipt.txt"):
                archive.addfile(tarfile.TarInfo(name))
        with self.assertRaisesRegex(OperationError, "duplicate paths"):
            inspect_archive(path)

    def test_archive_extracts_into_isolated_directory_and_checks_contents(self):
        path = self.archive()
        destination = self.root / "isolated"
        files = inspect_archive(path, destination)
        restored = destination / "media/synthetic-receipt.txt"
        self.assertEqual(restored.read_bytes(), b"explicit synthetic fixture")
        self.assertEqual(files["media/synthetic-receipt.txt"]["sha256"], digest(restored))

    def test_failed_dump_restarts_only_originally_running_writers(self):
        compose = Mock()
        compose.status.return_value = {"postgres": {"State": "running"}, "web": {"State": "running"},
                                       "worker": {"State": "running"}, "beat": {"State": "exited"}}
        compose.sql.return_value = "public.example|2\n"
        def run(*args, **kwargs):
            if args[0] == "exec":
                raise OperationError("synthetic dump failure")
        compose.run.side_effect = run
        with self.assertRaises(OperationError):
            backup(compose, self.root)
        self.assertEqual(compose.run.call_args_list[-1].args, ("start", "web", "worker"))
        manifest = json.loads(next(self.root.glob("*/manifest.json")).read_text())
        self.assertFalse(manifest["complete"])
        self.assertTrue(manifest["writers_resumed"])

    def test_backup_folder_is_private_before_anything_is_written(self):
        compose = Mock()
        compose.status.return_value = {"postgres": {"State": "running"}}
        compose.sql.return_value = "public.example|2\n"
        observed = []

        def run(*args, **kwargs):
            observed.append(verify_private(Path(kwargs["output_file"].name).parent))
            raise OperationError("synthetic dump failure")

        compose.run.side_effect = run
        with self.assertRaises(OperationError):
            backup(compose, self.root / "backups")
        self.assertEqual(observed, [True])
        self.assertTrue(verify_private(next(self.root.glob("backups/*/manifest.json"))))

    def exposure(self, *lines, **environment):
        path = self.root / "local.env"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with patch.dict("os.environ", environment):
            Compose(path).check_exposure()

    def test_verification_refuses_published_secrets_wildcard_hosts_and_public_addresses(self):
        example = read_env_file(ROOT / "config/local.env.example")
        safe = ("DJANGO_SECRET_KEY=synthetic-long-random-key", "DB_PASSWORD=synthetic-long-random-password")
        for lines in ((f"DJANGO_SECRET_KEY={example['DJANGO_SECRET_KEY']}", safe[1]),
                      (safe[0], f'DB_PASSWORD="{example["DB_PASSWORD"]}"'),
                      (*safe, "ALLOWED_HOSTS=localhost,*"),
                      (*safe, "ALFRED_BIND_ADDRESS=0.0.0.0"),
                      (*safe, "ALFRED_BIND_ADDRESS=::"),
                      (*safe, "ALFRED_BIND_ADDRESS=8.8.8.8"),
                      (*safe, "ALFRED_BIND_ADDRESS=alfred.example.com")):
            with self.subTest(lines=lines), self.assertRaises(OperationError):
                self.exposure(*lines)
        with self.assertRaises(OperationError):
            self.exposure(*safe, "ALFRED_BIND_ADDRESS=192.168.1.20", ALFRED_BIND_ADDRESS="0.0.0.0")

    def test_verification_accepts_loopback_and_private_lan_addresses(self):
        safe = ("DJANGO_SECRET_KEY=synthetic-long-random-key", "DB_PASSWORD=synthetic-long-random-password")
        with patch.dict("os.environ"):
            os.environ.pop("ALFRED_BIND_ADDRESS", None)
            self.exposure(*safe)
            for address in ("127.0.0.1", "192.168.1.20", "10.0.0.5", "fd00::5"):
                with self.subTest(address=address):
                    self.exposure(*safe, f"ALFRED_BIND_ADDRESS={address}")

    def test_exposure_failure_blocks_acceptance_and_leaks_no_value(self):
        compose = Mock()
        compose.check_exposure.side_effect = OperationError("Replace the example DB_PASSWORD in the local environment file")
        summary = verify(compose, self.root / "proof.json")
        self.assertFalse(summary["accepted"])
        self.assertEqual(summary["blockers"], ["Replace the example DB_PASSWORD in the local environment file"])
        compose.status.assert_not_called()

    def test_failed_restart_is_recorded_in_backup_manifest(self):
        compose = Mock()
        compose.status.return_value = {"postgres": {"State": "running"}, "web": {"State": "running"}}
        compose.sql.return_value = "public.example|2\n"
        archive = self.archive()

        def run(*args, **kwargs):
            if args[0] == "exec":
                kwargs["output_file"].write(b"synthetic dump")
            elif args[0] == "run":
                kwargs["output_file"].write(archive.read_bytes())
            elif args[0] == "start":
                raise OperationError("synthetic restart failure")

        compose.run.side_effect = run
        with self.assertRaisesRegex(OperationError, "restart failure"):
            backup(compose, self.root / "backups")
        manifest = json.loads(next(self.root.glob("backups/*/manifest.json")).read_text())
        self.assertTrue(manifest["complete"])
        self.assertFalse(manifest["writers_resumed"])

    def test_failure_during_stop_still_attempts_restart(self):
        compose = Mock()
        compose.status.return_value = {"postgres": {"State": "running"}, "web": {"State": "running"}}
        compose.run.side_effect = [OperationError("stop failed"), None]
        with self.assertRaises(OperationError):
            backup(compose, self.root)
        self.assertEqual(compose.run.call_args_list[-1].args, ("start", "web"))

    def test_stopped_database_is_refused_without_writing_backup(self):
        compose = Mock()
        compose.status.return_value = {"postgres": {"State": "exited"}}
        with self.assertRaises(OperationError):
            backup(compose, self.root)
        compose.run.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_incomplete_backup_is_refused_before_connecting_to_docker(self):
        write_json(self.root / "manifest.json", {"complete": False})
        compose = Mock()
        with self.assertRaises(OperationError):
            restore_check(compose, self.root)
        compose.preflight.assert_not_called()

    def complete_manifest(self):
        (self.root / "database.dump").write_bytes(b"synthetic dump")
        archive = self.archive()
        manifest = {"version": 1, "kind": "local_compose_backup", "complete": True, "row_counts": {"public.example": 2},
                    "sha256": {name: digest(self.root / name) for name in ("database.dump", "files.tar.gz")},
                    "files": inspect_archive(archive)}
        write_json(self.root / "manifest.json", manifest)

    def test_malformed_or_unsupported_manifest_is_refused_before_docker(self):
        self.complete_manifest()
        original = json.loads((self.root / "manifest.json").read_text())
        for change in ({"version": 2}, {"sha256": {}}, {"row_counts": {"public.example": True}},
                       {"files": {"media/receipt.txt": {"size": -1, "sha256": "a" * 64}}}):
            with self.subTest(change=change):
                write_json(self.root / "manifest.json", {**original, **change})
                compose = Mock()
                with self.assertRaises(OperationError):
                    restore_check(compose, self.root)
                compose.preflight.assert_not_called()

    def test_unsafe_archive_is_refused_before_docker_even_with_matching_checksum(self):
        self.complete_manifest()
        archive = self.archive("media/../../outside")
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["sha256"]["files.tar.gz"] = digest(archive)
        write_json(self.root / "manifest.json", manifest)
        compose = Mock()
        with self.assertRaisesRegex(OperationError, "unsafe path"):
            restore_check(compose, self.root)
        compose.preflight.assert_not_called()

    def test_file_manifest_mismatch_is_refused_before_docker(self):
        self.complete_manifest()
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["files"] = {}
        write_json(self.root / "manifest.json", manifest)
        compose = Mock()
        with self.assertRaisesRegex(OperationError, "file manifest differs"):
            restore_check(compose, self.root)
        compose.preflight.assert_not_called()

    def test_checksum_mismatch_refused_before_database_creation(self):
        self.complete_manifest()
        (self.root / "database.dump").write_bytes(b"corrupt")
        compose = Mock()
        with self.assertRaises(OperationError):
            restore_check(compose, self.root)
        compose.preflight.assert_not_called()

    def test_restore_failure_cleans_only_generated_database_and_records_failure(self):
        self.complete_manifest()
        compose = Mock(prefix=["docker", "compose"], env={})
        with patch("scripts.local_stack_ops.subprocess.run", return_value=Mock(returncode=1)):
            with self.assertRaises(OperationError):
                restore_check(compose, self.root)
        summary = json.loads((self.root / "restore_check.json").read_text())
        self.assertFalse(summary["accepted"])
        self.assertTrue(summary["cleanup_complete"])
        self.assertFalse(summary["live_database_modified"])
        command = compose.run.call_args_list[-1].args[-1]
        self.assertEqual(command, 'exec dropdb -U "$POSTGRES_USER" ' + summary["database"])

    def test_matching_restore_counts_and_files_record_accepted_isolated_proof(self):
        self.complete_manifest()
        compose = Mock(prefix=["docker", "compose"], env={})
        compose.sql.return_value = "public.example|2\n"
        with patch("scripts.local_stack_ops.subprocess.run", return_value=Mock(returncode=0)):
            summary = restore_check(compose, self.root)
        self.assertTrue(summary["accepted"])
        self.assertEqual(summary["restored_file_count"], 1)
        self.assertTrue(summary["cleanup_complete"])

    def test_cleanup_failure_cannot_record_an_accepted_restore(self):
        self.complete_manifest()
        compose = Mock(prefix=["docker", "compose"], env={})
        compose.sql.return_value = "public.example|2\n"
        compose.run.side_effect = [None, OperationError("synthetic cleanup failure")]
        with patch("scripts.local_stack_ops.subprocess.run", return_value=Mock(returncode=0)):
            with self.assertRaisesRegex(OperationError, "cleanup failure"):
                restore_check(compose, self.root)
        summary = json.loads((self.root / "restore_check.json").read_text())
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["cleanup_complete"])

    def test_row_count_mismatch_cleans_isolated_database_and_records_failure(self):
        self.complete_manifest()
        compose = Mock(prefix=["docker", "compose"], env={})
        compose.sql.return_value = "public.example|3\n"
        with patch("scripts.local_stack_ops.subprocess.run", return_value=Mock(returncode=0)):
            with self.assertRaisesRegex(OperationError, "row counts differ"):
                restore_check(compose, self.root)
        summary = json.loads((self.root / "restore_check.json").read_text())
        self.assertFalse(summary["accepted"])
        self.assertTrue(summary["cleanup_complete"])
        self.assertTrue(compose.run.call_args.args[-1].endswith(summary["database"]))

    def test_timed_out_verification_check_does_not_skip_remaining_checks(self):
        compose = Mock()
        compose.status.return_value = {name: {"State": "running", "Health": "healthy"} for name in SERVICES}
        compose.run.side_effect = [subprocess.TimeoutExpired("synthetic check", 180), None, None, None, None]
        summary = verify(compose, self.root / "proof.json")
        self.assertFalse(summary["accepted"])
        self.assertEqual(summary["blockers"], ["migrations_current"])
        self.assertTrue(summary["checks"]["worker_ping"])
        self.assertEqual(compose.run.call_count, 5)

    def test_missing_docker_records_blocker_without_claiming_runtime_success(self):
        compose = Mock()
        compose.preflight.side_effect = OperationError("Docker unavailable")
        summary = verify(compose, self.root / "proof.json")
        self.assertFalse(summary["accepted"])
        self.assertEqual(summary["blockers"], ["Docker unavailable"])
        self.assertTrue((self.root / "proof.json").exists())
