from transformers import pipeline

class RefactorAdvisor:

    def __init__(self):
        self.lm = pipeline("text-generation", model="gpt2")

    def recommend(self, content):
        prompt = (
            "Suggest safe refactoring improvements for this code. "
            "Provide non-destructive modifications ONLY:\n\n" + content[:4000]
        )
        return self.lm(prompt, max_length=512)[0]["generated_text"]

refactor_advisor = RefactorAdvisor()
