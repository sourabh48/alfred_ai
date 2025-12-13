import numpy as np
from sklearn.cluster import KMeans
from .vector_store import vector_store


class MemoryClustering:

    def cluster(self, k=8):
        db = vector_store.load()
        embeddings = [np.array(m["embedding"]) for m in db["memories"]]

        if len(embeddings) < k:
            return None  # Not enough data to cluster

        km = KMeans(n_clusters=k, random_state=42)
        labels = km.fit_predict(embeddings)

        # Assign cluster ids to metadata
        for i, mem in enumerate(db["memories"]):
            mem["metadata"]["cluster"] = int(labels[i])

        vector_store.save(db)

        return {"clusters": k, "status": "clustered"}


memory_clustering = MemoryClustering()
