import torch
import torch.nn as nn
import joblib
import os
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/salary_model/model.pt"
SCALER_PATH = "ml_models/alfred/salary_model/scaler.pkl"

class SalaryANN(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(5, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.fc(x)

class SalaryPredictor(BaseModelAdapter):

    def load(self):
        self.scaler = joblib.load(SCALER_PATH)
        self.model = SalaryANN()
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        self.model.eval()

    def preprocess(self, x):
        return torch.tensor(self.scaler.transform([x]), dtype=torch.float32)

    def predict(self, x):
        x = self.preprocess(x)
        with torch.no_grad():
            output = self.model(x)
        return output.item()

salary_predictor = SalaryPredictor()
