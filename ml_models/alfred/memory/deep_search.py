from .memory_retriever import memory_retriever
from .internet_retriever import internet_retriever
from .time_index import time_index
from .clustering import memory_clustering
from .graph_memory import graph_memory
from .vector_store import vector_store
import numpy as np


class DeepSearchEngine:

    def query(self, text, include_internet=False):
        # 1. Get memory results
        local_results = memory_retriever.retrieve(text)

        # 2. Apply time-weighted ranking
        for r in local_results:
            r["weighted_score"] = r["score"] * time_index.time_weight(r["timestamp"]) * r["importance"]

        local_results.sort(key=lambda x: x["weighted_score"], reverse=True)

        final_results = local_results[:5]

        # 3. Graph-based chain reasoning
        db = vector_store.load()
        graph_memory.build_graph(db["memories"])
        reasoning_path_ids = graph_memory.trace_reasoning_path(0)

        # Attach reasoning context
        reasoning_context = [
            db["memories"][i]["metadata"]["text"]
            for i in reasoning_path_ids
        ]

        # 4. Optional Internet augmentation
        internet_context = ""
        if include_internet:
            google = internet_retriever.fetch(f"https://www.google.com/search?q={text}")
            internet_context = google

        return {
            "results": final_results,
            "reasoning_context": reasoning_context,
            "internet_context": internet_context
        }


deep_search = DeepSearchEngine()
