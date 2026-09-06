import torch
from device import device


class DifferentiableTopology:

    def __init__(self, sdf_model):
        self.model = sdf_model

    def optimize_volume(self, target_volume, steps=200):
        scale = torch.tensor(1.0, requires_grad=True, device=device)
        opt = torch.optim.Adam([scale], lr=0.01)

        for _ in range(steps):
            pts = torch.rand(8000,3,device=device)*2-1
            field = self.model(pts*scale)
            occupancy = (field < 0).float()
            volume = occupancy.mean()
            loss = (volume-target_volume)**2
            opt.zero_grad()
            loss.backward()
            opt.step()

        return scale.item()
