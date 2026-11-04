from contextlib import contextmanager
import json
import os
import tempfile
from threading import RLock


_registry_lock = RLock()


@contextmanager
def _exclusive(directory):
    """The OS releases this lock if a process dies; a waiter gives up after about ten seconds."""
    with _registry_lock, open(os.path.join(directory, ".registry.lock"), "a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield


class AlfredModelRegistry:

    def __init__(self):
        base = os.getenv("ALFRED_REGISTRY_PATH", "ml_models/alfred/model_registry/")
        self.registry_path = os.path.join(base, "registry.json")
        os.makedirs(base, exist_ok=True)

        try:
            with _exclusive(base):
                try:
                    with open(self.registry_path, "x", encoding="utf-8") as f:
                        json.dump({}, f)
                except FileExistsError:
                    pass
                self.registry = self._load()
        except (ValueError, OSError):
            self.registry = {}

    def _load(self):
        with open(self.registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        if not isinstance(registry, dict):
            raise ValueError("Model registry must be a JSON object; preserve it for review.")
        return registry

    def get(self, model_name):
        return self.registry.get(model_name)

    def update(self, model_name, version, metadata=None):
        with _exclusive(os.path.dirname(self.registry_path)):
            registry = self._load()
            registry[model_name] = {"version": version, "metadata": metadata or {}}
            payload = json.dumps(registry, indent=4, allow_nan=False)
            descriptor, temporary = tempfile.mkstemp(prefix=".registry-", suffix=".tmp", dir=os.path.dirname(self.registry_path))
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as f:
                    f.write(payload)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, self.registry_path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            self.registry = registry

model_registry = AlfredModelRegistry()
