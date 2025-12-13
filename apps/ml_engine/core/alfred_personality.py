import json
import os

class AlfredPersonality:

    def __init__(self):
        base = os.getenv("ALFRED_PERSONALITY_PATH", "ml_models/alfred/personality/")
        self.personality_file = os.path.join(base, "traits.json")
        self.adaptive_file = os.path.join(base, "adaptive_traits.json")

        self.core_traits = self._load(self.personality_file)
        self.adaptive_traits = self._load(self.adaptive_file)

    def _load(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_personality(self):
        """Return Alfred's personality profile (static + learned)."""
        return {
            "core": self.core_traits,
            "adaptive": self.adaptive_traits
        }

    def update_trait(self, key, value):
        """Alfred continuously learns personality traits."""
        self.adaptive_traits[key] = value
        with open(self.adaptive_file, "w", encoding="utf-8") as f:
            json.dump(self.adaptive_traits, f, indent=4)

alfred_personality = AlfredPersonality()
