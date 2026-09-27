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
    from PIL import Image, ImageTk

    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ALFRED.Desktop")
    window = tk.Tk()
    window.title("ALFRED")
    assets = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon = assets / "static" / "alfred.ico"
    if os.name == "nt" and icon.is_file():
        window.iconbitmap(default=str(icon))
    window.resizable(False, False)
    width, height = 530, 282
    window.geometry(f"{width}x{height}+{(window.winfo_screenwidth()-width)//2}+{(window.winfo_screenheight()-height)//2}")
    background, foreground, muted, accent = "#0d1f2e", "#f1f5f9", "#b4c8d4", "#2dd4bf"
    window.configure(background=background)
    frame = tk.Frame(window, background=background, padx=28, pady=24)
    frame.pack(fill="both", expand=True)
    heading = tk.Frame(frame, background=background)
    heading.pack(fill="x", pady=(0, 22))
    if icon.is_file():
        with Image.open(icon) as source:
            logo = ImageTk.PhotoImage(source.convert("RGBA").resize((52, 52)), master=window)
        logo_label = tk.Label(heading, image=logo, background=background)
        logo_label.image = logo
        logo_label.pack(side="left", padx=(0, 14))
    titles = tk.Frame(heading, background=background)
    titles.pack(side="left")
    tk.Label(titles, text="ALFRED", font=("Segoe UI", 20, "bold"),
             background=background, foreground=foreground).pack(anchor="w")
    tk.Label(titles, text="Your personal workspace", font=("Segoe UI", 10),
             background=background, foreground=muted).pack(anchor="w")
    wording = "Opening your workspace" if args.command == "start" else "Finishing work and stopping"
    tk.Label(frame, text=wording, font=("Segoe UI", 12, "bold"),
             background=background, foreground=foreground).pack(anchor="w", pady=(0, 8))
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("Alfred.Horizontal.TProgressbar", troughcolor="#203a4b", background=accent,
                    bordercolor="#203a4b", lightcolor=accent, darkcolor=accent)
    progress = ttk.Progressbar(frame, mode="indeterminate", length=474,
                               style="Alfred.Horizontal.TProgressbar")
    progress.pack(fill="x")
    progress.start(12)
    detail = ("First launch may take a moment. Look for the ALFRED icon\nin the Windows tray once it is ready."
              if args.command == "start" else "Active jobs can finish safely. Your accounts and documents\nremain in your local data folder.")
    tk.Label(frame, text=detail, font=("Segoe UI", 10), justify="left",
             background=background, foreground=muted).pack(anchor="w", pady=(12, 0))
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
