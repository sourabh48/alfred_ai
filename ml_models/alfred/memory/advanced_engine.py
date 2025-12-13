import math
import time

class TimeWeightedIndex:

    def time_weight(self, timestamp):
        days = (time.time() - timestamp) / 86400

        # Soft exponential decay (keeps old memories but lowers priority)
        return math.exp(-0.03 * days)

    def combined_score(self, memory):
        base = memory.get("importance_score", 1)
        t = self.time_weight(memory["timestamp"])
        emotional = memory.get("emotional_intensity", 0.5)

        return (base * 0.6) + (t * 0.3) + (emotional * 0.1)

time_index = TimeWeightedIndex()
