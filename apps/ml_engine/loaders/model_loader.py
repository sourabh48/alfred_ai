import joblib
import torch
import tensorflow as tf

class ModelLoader:

    def load_sklearn(self, path):
        return joblib.load(path)

    def load_pytorch(self, path):
        return torch.load(path, map_location="cpu")

    def load_tensorflow(self, path):
        return tf.keras.models.load_model(path)

model_loader = ModelLoader()
