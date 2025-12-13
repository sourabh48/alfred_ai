import torch
import torch.nn as nn
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/relationship_siamese/model.pt"

class SiameseNet(nn.Module):

    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(10, 32),
            nn.ReLU(),
            nn.Linear(32, 8)
        )

    def forward_once(self, x):
        return self.fc(x)

    def forward(self, x1, x2):
        out1 = self.forward_once(x1)
        out2 = self.forward_once(x2)
        return torch.nn.functional.cosine_similarity(out1, out2)

class RelationshipSiameseAdapter(BaseModelAdapter):

    def load(self):
        self.model = SiameseNet()
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        self.model.eval()

    def predict(self, personA, personB):
        t1 = torch.tensor([personA], dtype=torch.float32)
        t2 = torch.tensor([personB], dtype=torch.float32)
        with torch.no_grad():
            return float(self.model(t1, t2))

relationship_siamese = RelationshipSiameseAdapter()
