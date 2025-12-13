import ast

class PerformanceProfiler:

    def analyze_ast(self, code):
        try:
            tree = ast.parse(code)
        except:
            return {"error": True}

        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                issues.append("Nested loops detected — consider vectorization.")
            if isinstance(node, ast.Try):
                issues.append("Try block found — check exception handling cost.")

        return {"issues": issues}

performance_profiler = PerformanceProfiler()
