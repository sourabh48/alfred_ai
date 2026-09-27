"""Verify the real installer, upgrade and uninstaller with disposable local data.

An existing registered ALFRED installation is never replaced. The startup-entry
test temporarily owns the current user's ALFRED Run value and restores it in
finally. Any existing desktop shortcut is also restored. Neither the normal
data folder nor the live runtime is used.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
import winreg

import requests


ROOT = Path(__file__).resolve().parents[1]
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{D4BFC620-610B-4AF7-81BF-215ECAC7297B}_is1"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def registry_value(key_path, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path,
                            access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None


def set_startup(value):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, access=winreg.KEY_WRITE) as key:
        if value is None:
            try:
                winreg.DeleteValue(key, "ALFRED")
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(key, "ALFRED", 0, value[1], value[0])


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def restore_shortcut(path, original, owned_versions):
    """Restore a shortcut unless another process has changed it since install."""
    current = path.read_bytes() if path.exists() else None
    if current == original:
        return True
    if current is not None and current not in owned_versions:
        return False
    if original is None:
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(original)
    return True


def wait_for_runtime_exit(data):
    """Wait for OS cleanup before comparing SQLite's on-disk bytes."""
    state = json.loads((data / "artifacts/native/runtime.json").read_text(encoding="utf-8"))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    for pid in {state.get("pid"), state.get("worker_pid")} - {None}:
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # The recorded process no longer exists.
                continue
            raise ctypes.WinError(error)
        try:
            assert kernel.WaitForSingleObject(handle, 30000) == 0, "Stopped test process has not exited"
        finally:
            kernel.CloseHandle(handle)


def wait_for_uninstall(installed, log_path):
    """Inno's original EXE exits before its clone completes final callbacks."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            log = log_path.read_text(encoding="utf-8-sig", errors="replace")
        except (FileNotFoundError, PermissionError):
            log = ""
        if ("Uninstallation process succeeded." in log and "Log closed." in log
                and not (installed / "ALFRED.exe").exists()
                and registry_value(UNINSTALL_KEY, "InstallLocation") is None):
            return
        time.sleep(0.2)
    raise AssertionError("Uninstaller did not finish its final cleanup; inspect its log")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    installer, report_path = args.installer.resolve(), args.report.resolve()
    if report_path.exists():
        parser.error("report already exists; preserve prior evidence with a new path")
    if registry_value(UNINSTALL_KEY, "InstallLocation"):
        parser.error("an ALFRED installation is registered; use an isolated Windows user")
    desktop_folder = registry_value(
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders", "Desktop")
    if not desktop_folder:
        parser.error("cannot locate the desktop safely; refusing to overwrite its shortcut")
    desktop_shortcut = Path(os.path.expandvars(desktop_folder[0])) / "ALFRED.lnk"
    original_shortcut = desktop_shortcut.read_bytes() if desktop_shortcut.exists() else None
    owned_shortcuts = set()
    run = uuid.uuid4().hex[:10]
    work = ROOT / "artifacts" / "installer-tests" / ("lifecycle-" + run)
    work.mkdir(parents=True)
    installed = work / "Program Files O'Brien" / "ALFRED"
    data = work / "data with spaces"
    native = installed / "ALFRED.exe"
    launcher = installed / "ALFRED Launcher.exe"
    uninstaller = installed / "unins000.exe"
    # All executable replacement and uninstall targets stay in this fresh folder.
    assert installed.resolve().is_relative_to(work.resolve())
    assert not installed.exists()
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    system = Path(os.environ.get("SystemRoot", "C:/Windows"))
    environment["PATH"] = os.pathsep.join(map(str, (system / "System32", system)))
    environment["ALFRED_DATA_DIR"] = str(data)
    environment["LOCALAPPDATA"] = str(work / "LocalAppData")
    original_startup = registry_value(RUN_KEY, "ALFRED")
    recovery_path = work / "original-windows-state.json"
    if original_shortcut is not None:
        (work / "original-desktop-shortcut.lnk").write_bytes(original_shortcut)
    recovery = {
        "install_dir": str(installed), "original_startup": original_startup,
        "desktop_shortcut": str(desktop_shortcut),
        "desktop_backup": str(work / "original-desktop-shortcut.lnk") if original_shortcut is not None else None,
        "test_startup": None,
    }
    # finally cannot run after a shutdown or forced termination. Keep recovery
    # values on disk before the installer or startup-entry test changes Windows.
    recovery_path.write_text(json.dumps(recovery, indent=2), encoding="utf-8")
    owned_startup = None
    startup_touched = False
    report = {"run": run, "created_at": datetime.now(timezone.utc).isoformat(),
              "installer_sha256": digest(installer), "data_dir": str(data),
              "install_dir": str(installed), "recovery_file": str(recovery_path),
              "passed": False, "checks": {}}

    def passed(name, detail=True):
        report["checks"][name] = detail
        print(f"PASS {name}: {detail}", flush=True)

    def execute(command, *, expect_success=True):
        result = subprocess.run(list(map(str, command)), cwd=work, env=environment,
                                capture_output=True, text=True, errors="replace",
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)
        if expect_success:
            assert result.returncode == 0, (command[0], result.returncode, result.stderr[-1000:])
        return result

    def install(label):
        execute([installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/NOICONS",
                 f"/DIR={installed}", f"/LOG={work / (label + '.log')}"])
        if desktop_shortcut.exists():
            owned_shortcuts.add(desktop_shortcut.read_bytes())
        location = registry_value(UNINSTALL_KEY, "InstallLocation")
        assert location and Path(location[0]).resolve() == installed.resolve()
        assert uninstaller.is_file() and (installed / "Uninstall ALFRED.cmd").is_file()

    def start():
        execute([launcher, "start", "--quiet", "--no-browser", "--data-dir", data, "--port", "8090"])
        state = json.loads((data / "artifacts/native/runtime.json").read_text(encoding="utf-8"))
        return f"http://127.0.0.1:{state['port']}"

    def uninstall(label):
        log_path = work / (label + '.log')
        execute([uninstaller, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                 f"/LOG={log_path}"])
        wait_for_uninstall(installed, log_path)

    session = requests.Session()
    session.trust_env = False
    try:
        install("install")
        passed("install_and_named_uninstaller")
        base = start()
        assert session.get(base + "/health/native/", timeout=30).json()["status"] == "ok"
        username, password = "installer_" + run, "InstallerProof936!"
        session.get(base + "/signup/", timeout=30).raise_for_status()
        session.post(base + "/signup/", data={
            "username": username, "password1": password, "password2": password,
            "email": username + "@example.test", "first_name": "Installer", "last_name": "Proof",
            "city": "Test City", "country": "India", "monthly_income": 0,
            "variable_income": 0, "rent_or_emi": 0, "csrfmiddlewaretoken": session.cookies["csrftoken"],
        }, timeout=90).raise_for_status()
        response = session.post(base + "/login/", data={
            "username": username, "password": password,
            "csrfmiddlewaretoken": session.cookies["csrftoken"],
        }, allow_redirects=False, timeout=30)
        assert response.status_code == 302
        for amount, category, classification, direction in ((42000, "income", "other", "credit"),
                                                           (1200, "groceries", "expense", "debit")):
            response = session.post(base + "/api/expenses/", json={
                "amount": amount, "category": category, "classification": classification,
                "direction": direction, "description": "Installer retention proof",
                "transaction_date": date.today().isoformat(),
            }, headers={"X-CSRFToken": session.cookies["csrftoken"]}, timeout=90)
            assert response.status_code == 201, response.text[:300]
        retained_file = data / "media" / "installer-retention.txt"
        retained_file.parent.mkdir(parents=True, exist_ok=True)
        retained_file.write_text("Synthetic installer retention proof", encoding="utf-8")
        file_hash = digest(retained_file)
        passed("installed_startup_without_system_python")

        install("upgrade")  # Stops the running test instance before replacing files.
        base = start()
        summary = session.get(base + "/api/expenses/dashboard/", timeout=90).json()["summary"]
        assert float(summary["current_month_net"]) == 40800, summary
        assert digest(retained_file) == file_hash
        passed("upgrade_retains_account_session_totals_and_file")
        execute([native, "stop", "--data-dir", data])
        wait_for_runtime_exit(data)
        db_hash = digest(data / "db.sqlite3")

        saved_native = installed / "ALFRED.exe.retained-for-test"
        native.rename(saved_native)
        try:
            native.write_bytes(b"Synthetic invalid executable: shutdown must fail")
            result = execute([uninstaller, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                              f"/LOG={work / 'blocked-uninstall.log'}"], expect_success=False)
            assert result.returncode != 0
            assert launcher.is_file() and saved_native.is_file() and uninstaller.is_file()
            assert registry_value(UNINSTALL_KEY, "InstallLocation")
            assert digest(data / "db.sqlite3") == db_hash
            passed("failed_shutdown_blocks_uninstall_before_file_removal")
        finally:
            saved_native.replace(native)

        uninstall("uninstall")
        assert registry_value(RUN_KEY, "ALFRED") == original_startup
        assert digest(data / "db.sqlite3") == db_hash and digest(retained_file) == file_hash
        passed("uninstall_retains_database_file_and_unrelated_startup")

        install("startup-cleanup-install")
        escaped_native = str(native).replace("'", "''")
        escaped_data = str(data).replace("'", "''")
        owned_startup = (f'powershell.exe -NoProfile -Command "& \'{escaped_native}\' start --data-dir \'{escaped_data}\' --no-browser"', winreg.REG_SZ)
        recovery["test_startup"] = owned_startup
        recovery_path.write_text(json.dumps(recovery, indent=2), encoding="utf-8")
        startup_touched = True
        set_startup(owned_startup)
        uninstall("startup-cleanup-uninstall")
        assert registry_value(RUN_KEY, "ALFRED") is None
        assert digest(data / "db.sqlite3") == db_hash and digest(retained_file) == file_hash
        passed("uninstall_removes_its_own_quoted_startup_entry")
        report["passed"] = True
    finally:
        session.close()
        report["original_desktop_shortcut_restored"] = restore_shortcut(
            desktop_shortcut, original_shortcut, owned_shortcuts)
        if not report["original_desktop_shortcut_restored"]:
            report["passed"] = False
            report["shortcut_restore_error"] = "Desktop shortcut changed externally; left that change untouched."
        if startup_touched:
            current = registry_value(RUN_KEY, "ALFRED")
            if current not in (None, original_startup, owned_startup):
                report["passed"] = False
                report["startup_restore_error"] = "Startup changed externally; left that change untouched."
            else:
                set_startup(original_startup)
        report["original_startup_restored"] = registry_value(RUN_KEY, "ALFRED") == original_startup
        report["passed"] = report["passed"] and report["original_startup_restored"]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report: {report_path}", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
