r"""Settings > Start with Windows: the current Windows user's own Run entry named ALFRED.

It is the same entry scripts/set_windows_autostart.ps1 writes and the uninstaller removes, with the same command, so
either can manage it. No administrator rights and no scheduled task. Reads and writes go through WMI StdRegProv on
HKEY_USERS\<SID>: the WMI service does them outside this process, so a packaged parent app's registry virtualisation
cannot hide a write from Windows, and the read-back is what Windows itself will run at sign-in.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings

from alfred_ai.services import online_services

ENTRY = "ALFRED"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"  # Windows Settings > Apps > Startup
BROWSER_SETTING = "ALFRED_START_OPENS_BROWSER"  # kept in config/local.env, so the choice survives while startup is off

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
function Reg($method, $arguments) {
    Invoke-CimMethod -ClassName StdRegProv -Namespace root/default -MethodName $method -Arguments ($arguments + @{hDefKey = [uint32]2147483651})
}
$run = "$sid\$env:ALFRED_STARTUP_RUN_KEY"; $approved = "$sid\$env:ALFRED_STARTUP_APPROVED_KEY"; $name = $env:ALFRED_STARTUP_ENTRY
if ($env:ALFRED_STARTUP_ACTION -eq 'set') {
    [void](Reg CreateKey @{sSubKeyName = $run})
    $r = Reg SetStringValue @{sSubKeyName = $run; sValueName = $name; sValue = $env:ALFRED_STARTUP_COMMAND}
    if ($r.ReturnValue -ne 0) { throw "Windows refused the startup entry ($($r.ReturnValue))." }
    [void](Reg DeleteValue @{sSubKeyName = $approved; sValueName = $name})  # no value = allowed in Windows Startup apps
}
if ($env:ALFRED_STARTUP_ACTION -eq 'remove') {
    $r = Reg DeleteValue @{sSubKeyName = $run; sValueName = $name}
    if ($r.ReturnValue -notin 0, 2) { throw "Windows refused to remove the startup entry ($($r.ReturnValue))." }
}
$value = Reg GetStringValue @{sSubKeyName = $run; sValueName = $name}
$flag = Reg GetBinaryValue @{sSubKeyName = $approved; sValueName = $name}
@{command = $(if ($value.ReturnValue -eq 0) { [string]$value.sValue } else { '' }); approved = [int[]]@(if ($flag.ReturnValue -eq 0) { $flag.uValue })} | ConvertTo-Json -Compress
"""


def _wmi(action="", command=""):
    """Run the StdRegProv script; returns {"command": str, "approved": [bytes]}. Values travel in environment variables."""
    if os.name != "nt":
        raise OSError("Start with Windows works only on Windows.")
    shell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    env = {**os.environ, "ALFRED_STARTUP_ACTION": action, "ALFRED_STARTUP_COMMAND": command, "ALFRED_STARTUP_ENTRY": ENTRY,
           "ALFRED_STARTUP_RUN_KEY": RUN_KEY, "ALFRED_STARTUP_APPROVED_KEY": APPROVED_KEY}
    encoded = base64.b64encode(_SCRIPT.encode("utf-16-le")).decode("ascii")
    done = subprocess.run([str(shell), "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                          capture_output=True, text=True, timeout=60, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    if done.returncode:
        message = (done.stderr or done.stdout).strip()
        raise OSError(message.splitlines()[0] if message else "Windows did not answer.")
    return json.loads(done.stdout)


def data_folder() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR)


def command(open_browser: bool) -> str:
    """The exact command set_windows_autostart.ps1 registers for this copy of ALFRED and its data folder."""
    data, flag = str(data_folder()).rstrip("\\"), "" if open_browser else " --no-browser"
    if getattr(sys, "frozen", False):  # ALFRED.exe has a console, so a hidden PowerShell parent starts it
        shell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        literal = lambda value: str(value).replace("'", "''")
        launch = f"& '{literal(sys.executable)}' start --data-dir '{literal(data)}'{flag}; exit $LASTEXITCODE"
        return f'"{shell}" -NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -Command "{launch}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")  # a source checkout: windowless Python, no console
    return f'"{pythonw}" "{Path(__file__).resolve().parents[2] / "alfred_native.py"}" start --data-dir "{data}"{flag}'


def _status(found: dict) -> dict:
    current = found.get("command") or ""
    approved = found.get("approved") or []
    blocked = bool(current) and bool(approved) and approved[0] % 2 == 1  # odd first byte = switched off in Windows Startup apps
    opens = ("--no-browser" not in current) if current else os.environ.get(BROWSER_SETTING) == "true"
    return {"available": True, "on": bool(current) and not blocked, "registered": bool(current), "turned_off_in_windows": blocked,
            "opens_browser": opens, "command": current, "this_copy": current in (command(True), command(False)),
            "expected": command(opens)}


def status() -> dict:
    try:
        return _status(_wmi())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"available": False, "error": str(error) or "Windows did not answer."}


def save(on: bool, open_browser: bool) -> dict:
    """Store the browser choice for this PC, apply on/off to the Run entry, then read Windows back to confirm it."""
    wanted = command(open_browser)
    if on and len(wanted) > 260:
        raise ValueError("Windows startup entries are limited to 260 characters. Move ALFRED or its data folder to a shorter path.")
    online_services.save({BROWSER_SETTING: "true" if open_browser else ""})
    result = _status(_wmi("set" if on else "remove", wanted if on else ""))
    if result["command"] != (wanted if on else "") or result["on"] != on:
        raise OSError("Windows did not keep the change. Check Windows Settings > Apps > Startup.")
    return result
