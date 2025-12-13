class BaseModelAdapter:

    def __init__(self):
        self.model = None

    def load(self):
        raise NotImplementedError

    def predict(self, x):
        raise NotImplementedError

    def preprocess(self, x):
        return x

    def postprocess(self, output):
        return output
