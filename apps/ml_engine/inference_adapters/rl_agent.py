from stable_baselines3 import PPO
import os
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/rl_agent/model.zip"

class RLFinanceAgent(BaseModelAdapter):

    def load(self):
        self.model = PPO.load(MODEL_PATH)

    def predict(self, state):
        action, _ = self.model.predict(state)
        return float(action)

rl_agent = RLFinanceAgent()
