import torch
import torch.nn as nn
import joblib
import os
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/expense_lstm/lstm_model.pt"

class ExpenseLSTM(nn.Module):

    def __init__(self, input_size=1, hidden=32):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden, batch_first=True)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x):
        output, _ = self.lstm(x)
        return self.fc(output[:, -1])

class ExpenseLSTMAdapter(BaseModelAdapter):

    def load(self):
        self.model = ExpenseLSTM()
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        self.model.eval()

    def preprocess(self, seq):
        seq = [[s] for s in seq]  # shape → batch, seq, features
        return torch.tensor([seq], dtype=torch.float32)

    def predict(self, seq):
        x = self.preprocess(seq)
        with torch.no_grad():
            return self.model(x).item()

expense_lstm = ExpenseLSTMAdapter()
