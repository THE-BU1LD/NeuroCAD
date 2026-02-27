# cad_neural.py

import torch
import torch.nn as nn

class NeuralSDF(nn.Module):

    def __init__(self, hidden=128):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(3, hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden),
            nn.GELU(),
            nn.Linear(hidden, 1)
        )

    def forward(self, x):
        return self.model(x)

    def wrap(self, sdf_func):
        def refined(x):
            base = sdf_func(x)
            correction = self.forward(x).squeeze(-1)
            return base + 0.01 * correction
        return refined