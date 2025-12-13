import numpy as np

class GraphMemory:

    def __init__(self):
        self.graph = {}  # adjacency list

    def add_node(self, mid, vector):
        self.graph[mid] = {"vector": vector, "edges": []}

    def add_edge(self, m1, m2, weight):
        self.graph[m1]["edges"].append({"to": m2, "weight": float(weight)})

    def build_graph(self, memories):
        # Create nodes
        for i, mem in enumerate(memories):
            self.add_node(i, np.array(mem["embedding"]))

        # Create weighted edges using cosine similarity
        def cosine(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        for i in range(len(memories)):
            for j in range(i+1, len(memories)):
                v1 = np.array(memories[i]["embedding"])
                v2 = np.array(memories[j]["embedding"])
                w = cosine(v1, v2)

                if w > 0.40:  # threshold
                    self.add_edge(i, j, w)
                    self.add_edge(j, i, w)

    def trace_reasoning_path(self, start_id, depth=3):
        visited = set()
        path = []

        def dfs(node, d):
            if d == 0 or node in visited:
                return
            visited.add(node)
            path.append(node)

            edges = sorted(
                self.graph[node]["edges"],
                key=lambda e: e["weight"],
                reverse=True
            )

            for e in edges[:3]:
                dfs(e["to"], d-1)

        dfs(start_id, depth)
        return path


graph_memory = GraphMemory()
