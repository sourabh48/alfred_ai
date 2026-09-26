from argparse import Namespace
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from alfred_launcher import native_command, run_native


class NativeLauncherTests(unittest.TestCase):
    def test_packaged_launcher_uses_sibling_executable_and_preserves_paths(self):
        with tempfile.TemporaryDirectory(prefix="alfred launcher ") as folder:
            native = Path(folder) / "ALFRED.exe"
            native.touch()
            args = Namespace(command="start", data_dir=r"C:\Personal files\ALFRED", port=8001, no_browser=True)
            with patch("alfred_launcher.sys.frozen", True, create=True), patch("alfred_launcher.sys.executable", str(Path(folder) / "ALFRED Launcher.exe")):
                self.assertEqual(native_command(args), [str(native), "start", "--port", "8001", "--data-dir", args.data_dir, "--no-browser"])

    def test_child_cannot_inherit_an_unrelated_python_environment(self):
        args = Namespace(command="start", data_dir=None, port=8000, no_browser=True)
        with patch("alfred_launcher.native_command", return_value=["ALFRED.exe", "start"]), patch.dict(
            "alfred_launcher.os.environ", {"PYTHONHOME": "wrong", "PYTHONPATH": "wrong"}
        ), patch("alfred_launcher.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "ready", "")) as run:
            self.assertEqual(run_native(args), (0, "ready"))
        environment = run.call_args.kwargs["env"]
        self.assertNotIn("PYTHONHOME", environment)
        self.assertNotIn("PYTHONPATH", environment)
        self.assertEqual(environment["PYINSTALLER_RESET_ENVIRONMENT"], "1")

    def test_start_failure_and_timeout_are_reported(self):
        args = Namespace(command="start", data_dir=None, port=8000, no_browser=True)
        with patch("alfred_launcher.native_command", return_value=["ALFRED.exe", "start"]), patch(
            "alfred_launcher.subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "Startup failed")
        ):
            self.assertEqual(run_native(args), (1, "Startup failed"))
        with patch("alfred_launcher.native_command", return_value=["ALFRED.exe", "start"]), patch(
            "alfred_launcher.subprocess.run", side_effect=subprocess.TimeoutExpired("ALFRED.exe", 240)
        ):
            code, message = run_native(args)
        self.assertEqual(code, 1)
        self.assertIn("timed out", message)
