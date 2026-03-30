import json
import os

class AlfredModelRegistry:

    def __init__(self):
        base = os.getenv("ALFRED_REGISTRY_PATH", "ml_models/alfred/model_registry/")
        self.registry_path = os.path.join(base, "registry.json")
        os.makedirs(base, exist_ok=True)

        if not os.path.exists(self.registry_path):
            with open(self.registry_path, "w") as f:
                json.dump({}, f)

        self.registry = self._load()

    def _load(self):
        try:
            with open(self.registry_path, "r") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def get(self, model_name):
        return self.registry.get(model_name)

    def update(self, model_name, version, metadata=None):
        self.registry[model_name] = {
            "version": version,
            "metadata": metadata or {}
        }
        with open(self.registry_path, "w") as f:
            json.dump(self.registry, f, indent=4)

model_registry = AlfredModelRegistry()
