"""Bootstrap refusals must leave retained data and configuration untouched."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_windows.ps1"


@unittest.skipUnless(POWERSHELL, "PowerShell is required")
class WindowsSetupTests(unittest.TestCase):
    def test_setup_holds_native_locks_through_install_and_validation(self):
        from alfred_native import InstanceLock

        code = SCRIPT.read_text().split("    $SetupNative = @'\n", 1)[1].split("\n'@", 1)[0]
        with tempfile.TemporaryDirectory(prefix="alfred-setup-lock-") as folder:
            data = Path(folder)
            (data / "config").mkdir()
            key = data / "config/native.env"
            key.write_bytes(b"retained synthetic key")
            local_config = data / "config/local.env"
            local_config.write_bytes(b"retained synthetic provider config")
            phases = []

            def probe(phase):
                for name in ("instance.lock", "worker.lock"):
                    with self.assertRaises(OSError), InstanceLock(data, name):
                        pass
                self.assertEqual(key.read_bytes(), b"retained synthetic key")
                self.assertEqual(local_config.read_bytes(), b"retained synthetic provider config")
                phases.append(phase)

            with mock.patch.object(sys, "argv", ["-", str(data), "True", str(SCRIPT.parents[1])]), \
                 mock.patch("subprocess.run", side_effect=lambda argv, **kwargs: probe(tuple(argv[3:]))), \
                 mock.patch("alfred_native.configure", side_effect=lambda path: probe("configure")), \
                 mock.patch("django.core.management.execute_from_command_line", side_effect=lambda argv: probe(tuple(argv[1:]))):
                exec(compile(code, str(SCRIPT), "exec"), {})
            self.assertEqual(phases, [
                ("install", "--upgrade", "pip"),
                ("install", "-r", str(SCRIPT.parents[1] / "requirements.txt")),
                ("check",), "configure", ("check",), ("migrate", "--noinput"),
            ])
            with InstanceLock(data, "instance.lock"), InstanceLock(data, "worker.lock"):
                pass

    def test_retained_database_and_key_are_never_replaced(self):
        for with_key in (False, True):
            with self.subTest(with_key=with_key), tempfile.TemporaryDirectory(prefix="alfred-setup-guard-") as folder:
                data = Path(folder)
                database = data / "db.sqlite3"
                database.write_bytes(b"retained database sentinel")
                if with_key:
                    (data / "config").mkdir()
                    (data / "config" / "native.env").write_bytes(b"retained test key sentinel")
                before = {str(path.relative_to(data)): path.read_bytes() for path in data.rglob("*") if path.is_file()}
                result = subprocess.run(
                    [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
                     "-DataDirectory", str(data), "-MigrateFresh"],
                    capture_output=True, text=True, timeout=30,
                )
                self.assertNotEqual(result.returncode, 0)
                expected = "-MigrateFresh requires" if with_key else "Restore its private configuration"
                self.assertIn(expected, result.stdout + result.stderr)
                after = {str(path.relative_to(data)): path.read_bytes() for path in data.rglob("*") if path.is_file()}
                self.assertEqual(after, before)
