import time
from sentence_transformers import SentenceTransformer
from .vector_store import vector_store
from .memory_scoring import memory_scoring


class MemoryWriter:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")  # lightweight reliable model

    def write(self, text, memory_type, extra={}):
        embedding = self.model.encode(text)

        memory = {
            "text": text,
            "type": memory_type.value,
            "timestamp": time.time(),
            "financial_impact": extra.get("financial_impact", 0),
            "emotional_intensity": extra.get("emotional_intensity", 0),
            "behavior_shift": extra.get("behavior_shift", 0),
            "tags": extra.get("tags", [])
        }

        score = memory_scoring.total_score(memory)
        memory["importance_score"] = score

        vector_store.add_vector(embedding, memory)
        return memory


memory_writer = MemoryWriter()
