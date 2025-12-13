import json
import os
import numpy as np
from pathlib import Path


class VectorStore:

    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.memory_file = self.base_path / "memory_db.json"

        if not self.memory_file.exists():
            self.memory_file.write_text(json.dumps({"memories": []}, indent=4))

    def load(self):
        return json.loads(self.memory_file.read_text())

    def save(self, db):
        self.memory_file.write_text(json.dumps(db, indent=4))

    def add_vector(self, vector, metadata):
        db = self.load()
        db["memories"].append({
            "embedding": vector.tolist(),
            "metadata": metadata
        })
        self.save(db)

    def search(self, query_vector, top_k=5):
        db = self.load()
        vectors = db["memories"]

        def cosine(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        scored = []
        for item in vectors:
            score = cosine(np.array(item["embedding"]), query_vector)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


vector_store = VectorStore("ml_models/alfred/memory")
