"""Small desktop entry point for the self-contained Windows distribution."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading


def native_command(args):
    directory = (Path(sys.executable).parent if getattr(sys, "frozen", False)
                 else Path(__file__).resolve().parent / "dist" / "ALFRED")
    executable = directory / "ALFRED.exe"
    if not executable.is_file():
        raise FileNotFoundError("ALFRED.exe is missing. Extract the complete ZIP or reinstall ALFRED.")
    command = [str(executable), args.command, "--port", str(args.port)]
    if args.data_dir:
        command.extend(["--data-dir", args.data_dir])
    if args.no_browser:
        command.append("--no-browser")
    return command


def run_native(args):
    try:
        environment = os.environ.copy()
        # The child is a complete frozen application with its own bootloader.
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        for name in ("PYTHONHOME", "PYTHONPATH"):
            environment.pop(name, None)
        completed = subprocess.run(
            native_command(args), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=240, env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return completed.returncode, (completed.stdout + completed.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Open or stop ALFRED on this computer")
    parser.add_argument("command", nargs="?", default="start", choices=("start", "stop"))
    parser.add_argument("--data-dir")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="Run without the progress window")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if args.quiet:
        code, message = run_native(args)
        if sys.stdout:
            print(message)
        return code

    import tkinter as tk
    from tkinter import messagebox, ttk

    window = tk.Tk()
    window.title("ALFRED")
    assets = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon = assets / "static" / "alfred.ico"
    if os.name == "nt" and icon.is_file():
        window.iconbitmap(default=str(icon))
    window.resizable(False, False)
    width, height = 440, 190
    window.geometry(f"{width}x{height}+{(window.winfo_screenwidth()-width)//2}+{(window.winfo_screenheight()-height)//2}")
    window.configure(background="#f4f6fa")
    frame = ttk.Frame(window, padding=26)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="ALFRED", font=("Segoe UI", 19, "bold")).pack(anchor="w")
    wording = "Opening your workspace..." if args.command == "start" else "Saving work and stopping ALFRED..."
    ttk.Label(frame, text=wording, font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 12))
    progress = ttk.Progressbar(frame, mode="indeterminate", length=380)
    progress.pack(fill="x")
    progress.start(12)
    ttk.Label(frame, text="The first launch may take a little longer.", font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 0))
    window.protocol("WM_DELETE_WINDOW", window.iconify)
    results = queue.Queue()
    outcome = [1]

    def poll():
        try:
            code, message = results.get_nowait()
        except queue.Empty:
            window.after(100, poll)
            return
        outcome[0] = code
        if code:
            progress.stop()
            messagebox.showerror("ALFRED could not finish", message or "Please try again. Your saved data is retained.", parent=window)
        window.destroy()

    threading.Thread(target=lambda: results.put(run_native(args)), daemon=True).start()
    window.after(100, poll)
    window.mainloop()
    return outcome[0]


if __name__ == "__main__":
    raise SystemExit(main())
