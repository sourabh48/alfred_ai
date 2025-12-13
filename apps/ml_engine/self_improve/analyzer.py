from transformers import pipeline

class CodeAnalyzer:

    def __init__(self):
        self.lm = pipeline("text-generation", model="gpt2")

    def analyze(self, content):
        prompt = (
            "Analyze the following code for performance, structure, "
            "security issues, readability problems, and architecture flaws. "
            "Provide clear findings:\n\n" + content[:40000]
        )
        return self.lm(prompt, max_length=512)[0]["generated_text"]

code_analyzer = CodeAnalyzer()
