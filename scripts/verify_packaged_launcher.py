"""Exercise the real desktop progress window with isolated data and no Python PATH."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    root = Path(__file__).resolve().parents[1]
    data = root / "artifacts" / "launcher-tests" / ("data with spaces " + uuid.uuid4().hex[:8])
    data.mkdir(parents=True)
    native, launcher = bundle / "ALFRED.exe", bundle / "ALFRED Launcher.exe"
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    system = Path(os.environ.get("SystemRoot", "C:/Windows"))
    environment["PATH"] = os.pathsep.join(map(str, (system / "System32", system)))
    report = {"data_dir": str(data), "gui_window_observed": False, "passed": False,
              "system_python_on_path": False}
    flags = subprocess.CREATE_NO_WINDOW
    process = subprocess.Popen([str(launcher), "start", "--data-dir", str(data), "--port", "8050", "--no-browser"],
                               env=environment, creationflags=flags)
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def inspect_window(handle, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == process.pid and user32.IsWindowVisible(handle):
            rectangle = wintypes.RECT()
            user32.GetWindowRect(handle, ctypes.byref(rectangle))
            if rectangle.right - rectangle.left > 100:
                report["gui_window_observed"] = True
                screenshot = data / "launcher.png"
                if not screenshot.exists():
                    from PIL import ImageGrab
                    # Capture only our window, even when another app covers it.
                    ImageGrab.grab(window=handle).save(screenshot)
        return True

    try:
        deadline = time.monotonic() + 270
        while process.poll() is None and time.monotonic() < deadline:
            user32.EnumWindows(inspect_window, 0)
            time.sleep(0.1)
        assert process.poll() == 0, f"Launcher exit status: {process.poll()}"
        assert report["gui_window_observed"], "No desktop progress window was observed"
        state = json.loads((data / "artifacts/native/runtime.json").read_text(encoding="utf-8"))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{state['port']}/health/native/", timeout=10) as response:
            health = json.load(response)
        assert health["status"] == "ok" and health["instance"] == state["instance"], health
        report.update(passed=True, port=state["port"], launcher_exit=process.returncode)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        stopped = subprocess.run([str(native), "stop", "--data-dir", str(data)], env=environment,
                                 creationflags=flags, capture_output=True, text=True, timeout=180)
        report["stop_exit"] = stopped.returncode
        report["passed"] = report["passed"] and stopped.returncode == 0
        (data / "proof.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (root / "artifacts/ops/packaged_launcher_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
