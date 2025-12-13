import torch
import torch.nn as nn
import os
import numpy as np
from apps.ml_engine.inference_adapters.expense_lstm import ExpenseLSTM, MODEL_PATH
from apps.ml_engine.data_extractors.user_expenses import load_user_expense_history


def train_expense_lstm():
    df = load_user_expense_history()

    if df.empty:
        print("No expense data, skipping LSTM training.")
        return

    df["amount"] = df["amount"].astype(float)
    seq = df["amount"].values[-100:]  # last 100 entries

    X = []
    y = []
    window = 10

    for i in range(len(seq) - window):
        X.append(seq[i:i + window])
        y.append(seq[i + window])

    X = torch.tensor(np.array(X).reshape(-1, window, 1), dtype=torch.float32)
    y = torch.tensor(np.array(y), dtype=torch.float32).view(-1, 1)

    model = ExpenseLSTM()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    for epoch in range(50):
        optimizer.zero_grad()
        preds = model(X)
        loss = criterion(preds, y)
        loss.backward()
        optimizer.step()

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)

    print("Expense LSTM retrained.")
