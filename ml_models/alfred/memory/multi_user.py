from pathlib import Path
import json

class MultiUserMemory:

    def __init__(self, base_path="ml_models/alfred/memory/users"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True, parents=True)

    def get_user_memory_path(self, user_id):
        path = self.base_path / f"{user_id}.json"
        if not path.exists():
            path.write_text(json.dumps({"memories": []}, indent=4))
        return path

    def load(self, user_id):
        return json.loads(self.get_user_memory_path(user_id).read_text())

    def save(self, user_id, db):
        self.get_user_memory_path(user_id).write_text(json.dumps(db, indent=4))

    def add_memory(self, user_id, embedding, metadata):
        db = self.load(user_id)
        db["memories"].append({"embedding": embedding.tolist(), "metadata": metadata})
        self.save(user_id, db)


multi_user_memory = MultiUserMemory()
