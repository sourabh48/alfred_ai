r"""Windows entry point for ALFRED's local web server and durable task queue.

Source: .venv\Scripts\python.exe alfred_native.py start
Packaged: ALFRED.exe [start|stop|status] [--data-dir PATH] [--no-browser]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import webbrowser


FROZEN = getattr(sys, "frozen", False)
ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def data_directory(value=None):
    if value or os.environ.get("ALFRED_DATA_DIR"):
        return Path(value or os.environ["ALFRED_DATA_DIR"]).expanduser().resolve()
    if FROZEN:
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ALFRED"
    return Path(__file__).resolve().parent


def runtime_directory(data):
    path = data / "artifacts" / "native"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, payload):
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def read_state(data):
    try:
        return json.loads((runtime_directory(data) / "runtime.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def running_state(data):
    state = read_state(data)
    port = state.get("port")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        return None
    try:
        # Ignore machine proxy settings for the local control connection.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/health/native/", timeout=2) as response:
            payload = json.load(response)
        if payload.get("status") == "ok" and payload.get("instance") == state.get("instance"):
            return state
    except (OSError, ValueError):
        pass
    return None


def child_command(command, data, *extra):
    prefix = [sys.executable] if FROZEN else [sys.executable, str(Path(__file__).resolve())]
    return [*prefix, command, "--data-dir", str(data), *extra]


def spawn(command, data, *extra):
    log = runtime_directory(data) / ("worker.log" if command == "worker" else "server.log")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log.open("ab", buffering=0) as output:
        return subprocess.Popen(
            child_command(command, data, *extra), cwd=data, stdin=subprocess.DEVNULL,
            stdout=output, stderr=output, creationflags=flags,
        )


def configure(data):
    """Run before importing Django, the project, or any task module."""
    data.mkdir(parents=True, exist_ok=True)
    runtime_directory(data)
    config = data / "config"
    config.mkdir(exist_ok=True)
    import environ
    environ.Env.read_env(data / ".env")
    previous_secret = os.environ.get("DJANGO_SECRET_KEY", "alfred-local-development-key")
    secret_file = config / "native.env"
    if not secret_file.exists():
        try:
            with secret_file.open("x", encoding="utf-8") as output:
                output.write(f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n")
                if (data / "db.sqlite3").exists():
                    # Preserve existing signed sessions and encrypted email tokens.
                    output.write(f"DJANGO_SECRET_KEY_FALLBACKS={json.dumps([previous_secret])}\n")
        except FileExistsError:
            pass
    os.environ.pop("DJANGO_SECRET_KEY_FALLBACKS", None)
    environ.Env.read_env(secret_file, overwrite=True)
    if not os.environ.get("DJANGO_SECRET_KEY"):
        raise RuntimeError(f"Set DJANGO_SECRET_KEY in {secret_file}.")
    os.environ.update({
        "DJANGO_SETTINGS_MODULE": "alfred_ai.native_settings",
        "ALFRED_TASK_BACKEND": "huey",
        "ALFRED_LOCAL_RUNTIME": "true",
        "ALFRED_AUTO_TRAIN_ON_STARTUP": "false",
        "ALFRED_DATA_DIR": str(data),
        "ALFRED_REGISTRY_PATH": str(data / "ml_models" / "alfred" / "model_registry"),
    })
    os.chdir(data)
    import django
    django.setup()


class InstanceLock:
    """An OS lock is released on process exit, including a crashed process."""
    def __init__(self, data, name="instance.lock"):
        self.file = (runtime_directory(data) / name).open("a+b")

    def __enter__(self):
        try:
            return self._acquire()
        except Exception:
            self.file.close()
            raise

    def _acquire(self):
        self.file.seek(0)
        if os.name == "nt":
            import msvcrt
            if not self.file.read(1):
                self.file.write(b"0")
                self.file.flush()
            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self

    def __exit__(self, *_):
        self.file.close()


def parent_is_running(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT: still alive
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def worker(data, instance, parent_pid):
    # A surviving worker may still be finishing after its supervisor died.
    # Never recover claims while another consumer can still execute them.
    with InstanceLock(data, "worker.lock"):
        return consume(data, instance, parent_pid)


def consume(data, instance, parent_pid):
    os.environ["ALFRED_NATIVE_INSTANCE"] = instance
    configure(data)
    from alfred_ai import native_tasks  # noqa: F401 -- explicit task discovery for frozen builds
    from django.core.cache import cache
    from huey.contrib.djhuey import HUEY
    from huey.consumer import ConsumerStopped

    recovery = HUEY.storage.recover(HUEY.deserialize_task)
    write_json(runtime_directory(data) / "job-recovery.json", {"time": time.time(), **recovery})

    # A separate queue consumer with thread workers works on Windows.
    consumer = HUEY.create_consumer(workers=2, worker_type="thread", periodic=True)
    stop = runtime_directory(data) / f"worker-stop-{instance}"
    consumer.start()
    health_check = time.monotonic()
    try:
        while not stop.exists() and parent_is_running(parent_pid):
            cache.set("native:worker-heartbeat", {"instance": instance, "time": time.time()}, timeout=15)
            try:
                health_check = consumer.loop(health_check)
            except ConsumerStopped:
                break
    finally:
        # Complete in-flight tasks before closing. Queued tasks stay on disk.
        consumer.stop(graceful=True)
        cache.delete("native:worker-heartbeat")
        stop.unlink(missing_ok=True)


def serve(data, port):
    try:
        lock = InstanceLock(data)
        lock.__enter__()
    except OSError:
        print("ALFRED is already starting or running for this data folder.")
        return 0
    runtime = runtime_directory(data)
    instance = uuid.uuid4().hex
    os.environ["ALFRED_NATIVE_INSTANCE"] = instance
    state = {"instance": instance, "pid": os.getpid(), "status": "starting", "port": port}
    write_json(runtime / "runtime.json", state)
    child = server = None
    try:
        configure(data)
        from django.core.management import call_command
        from django.core.wsgi import get_wsgi_application
        from alfred_ai.services.native_web import create_native_server
        from alfred_ai.tasks import production_probe_task

        with sqlite3.connect(data / "db.sqlite3", timeout=30) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
        call_command("migrate", interactive=False, verbosity=1)
        call_command("collectstatic", interactive=False, verbosity=0)
        child = spawn("worker", data, "--instance", instance, "--parent-pid", str(os.getpid()))
        # This is an actual queued task, not eager execution or a process ping.
        probe = production_probe_task.delay(instance)
        result = probe.get(blocking=True, timeout=90)
        if result.get("probe_id") != instance:
            raise RuntimeError("The background worker did not return the startup probe.")
        application = get_wsgi_application()
        for candidate in range(port, min(port + 20, 65536)):
            try:
                server = create_native_server(application, candidate)
                state["port"] = candidate
                break
            except OSError as error:
                if getattr(error, "winerror", None) not in (10048, 10013) and error.errno != 98:
                    raise
        if server is None:
            raise RuntimeError("No free local port. Use --port to choose another port.")
        thread = threading.Thread(target=server.run, name="alfred-web", daemon=True)
        thread.start()
        state.update(status="running", worker_pid=child.pid, started_at=time.time())
        write_json(runtime / "runtime.json", state)
        print(f"ALFRED is ready at http://127.0.0.1:{state['port']}/", flush=True)
        restarts = []
        while not (runtime / f"stop-{instance}").exists():
            if not thread.is_alive():
                raise RuntimeError("The local web server stopped unexpectedly.")
            if child.poll() is not None:
                restarts = [stamp for stamp in restarts if time.time() - stamp < 60]
                if len(restarts) >= 3:
                    raise RuntimeError("The background worker repeatedly stopped. See worker.log.")
                restarts.append(time.time())
                child = spawn("worker", data, "--instance", instance, "--parent-pid", str(os.getpid()))
                state["worker_pid"] = child.pid
                write_json(runtime / "runtime.json", state)
            time.sleep(0.5)
    finally:
        state["status"] = "stopping"
        write_json(runtime / "runtime.json", state)
        if server is not None:
            server.close()
            server.task_dispatcher.shutdown(timeout=30)
        if child is not None and child.poll() is None:
            (runtime / f"worker-stop-{instance}").touch()
            child.wait()  # Do not cut off a running document import or model save.
        (runtime / f"stop-{instance}").unlink(missing_ok=True)
        state["status"] = "stopped"
        write_json(runtime / "runtime.json", state)
        lock.__exit__()
    return 0


def start(data, port, open_browser):
    state = running_state(data)
    if state is None:
        child = spawn("serve", data, "--port", str(port))
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            state = running_state(data)
            if state:
                break
            if child.poll() not in (None, 0):
                raise RuntimeError(f"ALFRED could not start. See {runtime_directory(data) / 'server.log'}")
            time.sleep(0.5)
        if state is None:
            raise RuntimeError(f"ALFRED is still starting or failed. See {runtime_directory(data) / 'server.log'}")
    url = f"http://127.0.0.1:{state['port']}/"
    print(f"ALFRED is running: {url}\nData folder: {data}")
    if open_browser:
        webbrowser.open(url)
    return 0


def stop(data):
    state = read_state(data)
    # PIDs can be reused after a reboot. OS locks identify our processes;
    # an unrelated process with the old PID must never affect stop behaviour.
    try:
        inactive = InstanceLock(data)
        inactive.__enter__()
    except OSError:
        pass  # A supervisor owns the folder; ask it to stop below.
    else:
        try:
            try:
                with InstanceLock(data, "worker.lock"):
                    state["status"] = "stopped"
                    write_json(runtime_directory(data) / "runtime.json", state)
            except OSError:
                print("The server has stopped; its background worker is finishing current work.")
                return 1
        finally:
            inactive.__exit__()
    if state.get("status") in ("starting", "running", "stopping") and state.get("instance"):
        (runtime_directory(data) / f"stop-{state['instance']}").touch()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            current = read_state(data)
            if current.get("status") == "stopped":
                print("ALFRED stopped. Your data and queued jobs are saved.")
                return 0
            time.sleep(0.5)
        print("Shutdown requested. ALFRED will stop after its current jobs finish.")
        return 1
    print("ALFRED is not running for this data folder.")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--ocr-worker":
        from alfred_ai.services.ocr_process import run_frozen_worker
        return run_frozen_worker(sys.argv[2:])
    parser = argparse.ArgumentParser(description="ALFRED local Windows application")
    parser.add_argument("command", nargs="?", default="start", choices=("start", "stop", "status", "serve", "worker", "jobs", "retry-job"))
    parser.add_argument("--job-id", help="Interrupted job ID shown by the jobs command")
    parser.add_argument("--data-dir")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--instance", default="")
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    data = data_directory(args.data_dir)
    if args.command in ("jobs", "retry-job"):
        configure(data)
        from alfred_ai import native_tasks  # noqa: F401
        from huey.contrib.djhuey import HUEY
        if args.command == "retry-job":
            if not args.job_id:
                parser.error("retry-job requires --job-id from the jobs command")
            HUEY.storage.retry_review(args.job_id, HUEY.deserialize_task)
            print("Reviewed job queued for another attempt.")
        else:
            print(json.dumps(HUEY.storage.review_jobs(HUEY.deserialize_task), indent=2))
        return 0
    if args.command == "serve":
        return serve(data, args.port)
    if args.command == "worker":
        if not args.instance or not args.parent_pid:
            parser.error("worker requires --instance and --parent-pid")
        return worker(data, args.instance, args.parent_pid)
    if args.command == "stop":
        return stop(data)
    if args.command == "status":
        state = running_state(data)
        print(json.dumps({"running": bool(state), "data_dir": str(data), "runtime": state or read_state(data)}, indent=2))
        return 0 if state else 1
    return start(data, args.port, not args.no_browser)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("ALFRED failed")
        if FROZEN and sys.stderr is None:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(error), "ALFRED could not start", 0x10)
        raise SystemExit(1)
