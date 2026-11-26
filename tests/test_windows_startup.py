"""Settings > Start with Windows: ALFRED's own entry in the current user's Run list, applied and read back through WMI."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from alfred_ai.services import windows_startup as startup

URL = "/api/settings/windows-startup/"


class FakeWindows:
    """The Run value and the Windows Startup apps flag, as StdRegProv would keep them."""
    def __init__(self, command="", approved=()):
        self.command, self.approved, self.calls = command, list(approved), []

    def __call__(self, action="", command=""):
        self.calls.append(action)
        if action == "set":
            self.command, self.approved = command, []
        elif action == "remove":
            self.command = ""
        return {"command": self.command, "approved": self.approved}


class WindowsStartupTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-startup-synthetic-")))
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root)}))
        os.environ.pop(startup.BROWSER_SETTING, None)
        self.windows = FakeWindows()
        self.enterContext(patch.object(startup, "_wmi", self.windows))
        users = get_user_model().objects
        self.owner = users.create_user(username="synthetic-startup-owner", password="pw-synthetic-1")
        self.family = users.create_user(username="synthetic-startup-family", password="pw-synthetic-2")

    def post(self, user, body):
        self.client.force_login(user)
        return self.client.post(URL, json.dumps(body), content_type="application/json")

    def test_commands_are_the_ones_the_startup_script_registers(self):
        """Same text as scripts/set_windows_autostart.ps1, so the script, the uninstaller and Settings share one entry."""
        native = Path(startup.__file__).resolve().parents[2] / "alfred_native.py"
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        self.assertEqual(startup.command(False), f'"{pythonw}" "{native}" start --data-dir "{self.root}" --no-browser')
        self.assertEqual(startup.command(True), f'"{pythonw}" "{native}" start --data-dir "{self.root}"')
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", r"C:\Apps\ALFRED's\ALFRED.exe"), \
                patch.dict(os.environ, {"ALFRED_DATA_DIR": r"D:\Data O'Neil", "SystemRoot": r"C:\Windows"}):
            self.assertEqual(startup.command(False), r'"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile '
                             r"""-NonInteractive -WindowStyle Hidden -Command "& 'C:\Apps\ALFRED''s\ALFRED.exe' start --data-dir 'D:\Data O''Neil' """
                             r'--no-browser; exit $LASTEXITCODE"')

    def test_turning_on_and_off_writes_the_entry_and_reads_windows_back(self):
        self.assertEqual(self.post(self.owner, {"on": True, "open_browser": False}).status_code, 200)
        self.assertEqual(self.windows.command, startup.command(False))
        result = self.client.get(URL).json()
        self.assertEqual((result["on"], result["opens_browser"], result["this_copy"], result["can_manage"]), (True, False, True, True))
        # The browser choice is kept per PC in config/local.env, so it survives while startup is off.
        result = self.post(self.owner, {"on": False, "open_browser": True}).json()
        self.assertEqual((result["on"], result["registered"], result["opens_browser"], self.windows.command), (False, False, True, ""))
        self.assertIn(f"{startup.BROWSER_SETTING}='true'", (self.root / "config" / "local.env").read_text(encoding="utf-8"))
        self.assertEqual(self.post(self.owner, {"on": True, "open_browser": True}).json()["command"], startup.command(True))
        self.assertNotIn("--no-browser", self.windows.command)

    def test_an_entry_switched_off_in_windows_shows_off_and_saving_switches_it_back_on(self):
        self.windows.command, self.windows.approved = startup.command(False), [3, 0, 0, 0]
        result = startup.status()
        self.assertEqual((result["on"], result["registered"], result["turned_off_in_windows"]), (False, True, True))
        self.assertTrue(startup.save(True, False)["on"])
        self.assertEqual(self.windows.approved, [])

    def test_another_copy_is_reported_and_a_change_windows_does_not_keep_is_an_error(self):
        self.windows.command = r'"D:\Old\pythonw.exe" "D:\Old\alfred_native.py" start --data-dir "D:\Old data" --no-browser'
        result = startup.status()
        self.assertEqual((result["on"], result["this_copy"], result["opens_browser"]), (True, False, False))
        with patch.object(startup, "_wmi", lambda action="", command="": {"command": "", "approved": []}):
            response = self.post(self.owner, {"on": True, "open_browser": False})
        self.assertEqual(response.status_code, 500)
        self.assertIn("Windows did not keep the change", response.json()["detail"])

    def test_only_the_manager_changes_it_and_input_is_checked_first(self):
        self.assertEqual(self.post(self.owner, {"on": "yes", "open_browser": False}).status_code, 400)
        response = self.post(self.family, {"on": True, "open_browser": False})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.client.get(URL).json()["can_manage"])
        self.assertEqual(self.windows.calls, [""])  # only the family member's read; nothing was written

    def test_unreadable_windows_is_shown_not_hidden(self):
        def broken(action="", command=""):
            raise OSError("Start with Windows works only on Windows.")
        with patch.object(startup, "_wmi", broken):
            self.assertEqual(startup.status(), {"available": False, "error": "Start with Windows works only on Windows."})


@unittest.skipUnless(os.name == "nt", "WMI StdRegProv is Windows only")
class StdRegProvRoundTripTests(unittest.TestCase):
    """The real WMI script, on a synthetic key of its own; the user's Run and Startup apps lists are never touched."""
    KEY = r"Software\ALFRED synthetic startup test"

    def tearDown(self):
        script = ("$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; foreach ($k in 'Run','Approved','') {"
                  " [void](Invoke-CimMethod -ClassName StdRegProv -Namespace root/default -MethodName DeleteKey"
                  f" -Arguments @{{hDefKey=[uint32]2147483651; sSubKeyName=(\"$sid\\{self.KEY}\\$k\").TrimEnd('\\')}}) }}")
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, timeout=60)

    def test_set_read_and_remove_reach_windows(self):
        value = r'''"C:\Synthetic Folder\pythonw.exe" "C:\it's here\alfred_native.py" start --data-dir "C:\Synthetic data" --no-browser'''
        with patch.multiple(startup, RUN_KEY=self.KEY + r"\Run", APPROVED_KEY=self.KEY + r"\Approved", ENTRY="ALFRED synthetic"):
            self.assertEqual(startup._wmi(), {"command": "", "approved": []})
            self.assertEqual(startup._wmi("set", value)["command"], value)
            self.assertEqual(startup._wmi("remove")["command"], "")
