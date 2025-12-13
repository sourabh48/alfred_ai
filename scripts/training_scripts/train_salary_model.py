import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import joblib
import os
from apps.ml_engine import SalaryANN, MODEL_PATH, SCALER_PATH
from sklearn.preprocessing import StandardScaler

def train_salary_model():
    df = pd.read_csv("salary_training_data.csv")

    X = df[["experience", "age", "city_index", "industry_index", "skill_score"]].values
    y = df["salary"].values

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    joblib.dump(scaler, SCALER_PATH)

    model = SalaryANN()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32).view(-1, 1)

    for epoch in range(200):
        optimizer.zero_grad()
        output = model(X_tensor)
        loss = criterion(output, y_tensor)
        loss.backward()
        optimizer.step()

    torch.save(model.state_dict(), MODEL_PATH)

if __name__ == "__main__":
    train_salary_model()
