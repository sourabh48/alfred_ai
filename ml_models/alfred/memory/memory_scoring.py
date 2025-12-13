import math
import time

class MemoryScoring:

    def compute_importance(self, memory):
        factors = [
            memory.get("financial_impact", 0),
            memory.get("emotional_intensity", 0),
            memory.get("behavior_shift", 0),
            1 if memory.get("event_type") in ("risk", "career") else 0
        ]
        return sum(factors)

    def recency_decay(self, timestamp):
        days = (time.time() - timestamp) / 86400
        return math.exp(-0.05 * days)

    def total_score(self, memory):
        imp = self.compute_importance(memory)
        rec = self.recency_decay(memory["timestamp"])
        return imp * rec


memory_scoring = MemoryScoring()
