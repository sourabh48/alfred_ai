import json
import os
import tempfile
from threading import RLock


_registry_lock = RLock()

class AlfredModelRegistry:

    def __init__(self):
        base = os.getenv("ALFRED_REGISTRY_PATH", "ml_models/alfred/model_registry/")
        self.registry_path = os.path.join(base, "registry.json")
        os.makedirs(base, exist_ok=True)

        with _registry_lock:
            try:
                with open(self.registry_path, "x", encoding="utf-8") as f:
                    json.dump({}, f)
            except FileExistsError:
                pass
            try:
                self.registry = self._load()
            except (ValueError, FileNotFoundError):
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
        # shortcut: process-local coordination; add an external writer lock before multi-process training.
        with _registry_lock:
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
