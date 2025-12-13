import os

class CodeScanner:

    def scan_project(self, root="F:/ALFRED/alfred_ai"):
        codebase = []

        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith((".py", ".html", ".css", ".js")):
                    path = os.path.join(dirpath, f)
                    try:
                        text = open(path, "r", encoding="utf-8", errors="ignore").read()
                        codebase.append({"path": path, "content": text})
                    except:
                        pass

        return codebase

code_scanner = CodeScanner()
