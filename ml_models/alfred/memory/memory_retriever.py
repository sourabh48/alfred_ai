from sentence_transformers import SentenceTransformer
from .vector_store import vector_store


class MemoryRetriever:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def retrieve(self, query, top_k=5):
        embedding = self.model.encode(query)
        results = vector_store.search(embedding, top_k)

        return [
            {
                "score": score,
                "text": item["metadata"]["text"],
                "type": item["metadata"]["type"],
                "timestamp": item["metadata"]["timestamp"],
                "importance": item["metadata"]["importance_score"],
                "tags": item["metadata"].get("tags", [])
            }
            for score, item in results
        ]


memory_retriever = MemoryRetriever()
