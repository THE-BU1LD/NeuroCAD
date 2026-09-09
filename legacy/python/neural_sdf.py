import torch
import torch.nn as nn
from device import device


class NeuralSDF(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3,128),
            nn.ReLU(),
            nn.Linear(128,128),
            nn.ReLU(),
            nn.Linear(128,1)
        )

    def forward(self,x):
        return self.net(x).squeeze(-1)


class NeuralTrainer:

    def __init__(self):
        self.model = NeuralSDF().to(device)
        self.opt = torch.optim.Adam(self.model.parameters(), lr=1e-4)

    def train_surface(self, verts, epochs=300):
        pts = torch.tensor(verts, device=device).float()
        target = torch.zeros(len(verts), device=device)

        for _ in range(epochs):
            pred = self.model(pts)
            loss = ((pred - target)**2).mean()
            self.opt.zero_grad()
            loss.backward()
            self.opt.step()

        return self.model
