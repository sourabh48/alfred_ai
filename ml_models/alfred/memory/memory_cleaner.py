import json
from .vector_store import vector_store
from .memory_scoring import memory_scoring


class MemoryCleaner:

    def prune_low_importance(self):
        db = vector_store.load()
        memories = db["memories"]

        kept = []
        for m in memories:
            meta = m["metadata"]
            if meta["importance_score"] > 0.4:  # threshold
                kept.append(m)

        db["memories"] = kept
        vector_store.save(db)
        return len(kept)


memory_cleaner = MemoryCleaner()
