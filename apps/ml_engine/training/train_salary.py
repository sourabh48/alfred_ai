import torch
import torch.nn as nn
import torch.optim as optim
import joblib
import os
from sklearn.preprocessing import StandardScaler
from apps.ml_engine.inference_adapters.salary_predictor import SalaryANN, MODEL_PATH, SCALER_PATH
from apps.ml_engine.data_extractors.user_profile import load_user_profiles

def train_salary_model():
    df = load_user_profiles()

    # Create synthetic features
    df["experience_years"] = df["date_joined"].apply(lambda x: 1)
    df["skill_score"] = 3.5

    features = ["experience_years", "monthly_income", "variable_income", "rent_or_emi", "skill_score"]
    X = df[features].values
    y = df["monthly_income"].values  # Predicting income growth

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(scaler, SCALER_PATH)

    model = SalaryANN()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32).view(-1, 1)

    for epoch in range(80):
        optimizer.zero_grad()
        pred = model(X_tensor)
        loss = criterion(pred, y_tensor)
        loss.backward()
        optimizer.step()

    torch.save(model.state_dict(), MODEL_PATH)
    print("Salary model retrained successfully.")
