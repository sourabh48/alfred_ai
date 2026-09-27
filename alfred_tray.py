"""A Windows notification-area icon owned by the running native supervisor.

Windows permits pystray's message loop on a dedicated thread:
https://pystray.readthedocs.io/en/latest/usage.html
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import threading
import webbrowser


class NativeTray:
    def __init__(self, data, instance, port, assets, on_stop, record):
        self.data = Path(data)
        self.instance = instance
        self.url = f"http://127.0.0.1:{port}/"
        self.assets = Path(assets)
        self.on_stop = on_stop
        self.record = record
        self.icon = None
        self.thread = None
        self.ready = threading.Event()
        self.closing = threading.Event()
        self.stopping = False

    def _record(self, status, **extra):
        try:
            self.record({"instance": self.instance, "pid": os.getpid(),
                         "status": status, "url": self.url, **extra})
        except OSError:
            logging.exception("Could not record ALFRED tray status")

    def open_workspace(self, *_):
        if not self.stopping:
            threading.Thread(target=webbrowser.open, args=(self.url,), daemon=True).start()

    def open_data(self, *_):
        os.startfile(str(self.data))

    def open_guide(self, *_):
        guide = self.assets / "guide" / "index.html"
        if not guide.is_file():
            guide = self.assets / "docs" / "guide" / "index.html"
        webbrowser.open(guide.resolve().as_uri())

    def request_stop(self, *_):
        if self.stopping:
            return
        # Use the supervisor's existing graceful shutdown, never kill its jobs.
        self.on_stop()
        self.mark_stopping()

    def mark_stopping(self):
        self.stopping = True
        if self.icon:
            try:
                self.icon.title = "ALFRED — finishing work and stopping"
                self.icon.update_menu()
            except Exception:
                logging.exception("Could not update ALFRED tray during shutdown")
        self._record("stopping", visible=bool(self.icon and self.icon.visible))

    def _setup(self, icon):
        try:
            if self.closing.is_set():
                icon.stop()
                return
            icon.visible = True
            self._record("running", visible=True, window_handle=getattr(icon, "_hwnd", None),
                         icon_id=0)  # The pinned pystray Win32 backend uses uID=0.
        except Exception:
            logging.exception("ALFRED notification icon could not be shown")
            self._record("unavailable", visible=False)
            icon.stop()
        finally:
            self.ready.set()

    def _run(self):
        try:
            import pystray
            from PIL import Image

            with Image.open(self.assets / "static" / "alfred.ico") as source:
                image = source.convert("RGBA")
            self.icon = pystray.Icon(
                "ALFRED", image, f"ALFRED — running at {self.url}",
                pystray.Menu(
                    pystray.MenuItem(lambda _: "ALFRED is stopping…" if self.stopping else "ALFRED is running",
                                     None, enabled=False),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Open ALFRED", self.open_workspace, default=True,
                                     enabled=lambda _: not self.stopping),
                    pystray.MenuItem("Installation guide", self.open_guide),
                    pystray.MenuItem("Open data folder", self.open_data),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Stop ALFRED", self.request_stop,
                                     enabled=lambda _: not self.stopping),
                ),
            )
            if not self.closing.is_set():
                self.icon.run(setup=self._setup)
        except Exception:
            # A missing desktop/shell must not bring down the web server.
            logging.exception("ALFRED notification icon is unavailable")
            self._record("unavailable", visible=False)
        finally:
            self.ready.set()

    def start(self):
        self.thread = threading.Thread(target=self._run, name="alfred-tray", daemon=True)
        self.thread.start()
        return self

    def close(self):
        self.closing.set()
        self.ready.wait(5)
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                logging.exception("Could not remove ALFRED tray icon")
        if self.thread:
            self.thread.join(timeout=5)
        self._record("stopped", visible=False)


def start_tray(data, state, assets, on_stop, record):
    if os.name != "nt" or os.environ.get("ALFRED_NO_TRAY") == "1":
        return None
    return NativeTray(data, state["instance"], state["port"], assets, on_stop, record).start()
