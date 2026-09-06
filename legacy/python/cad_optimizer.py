# cad_optimizer.py

import torch

class ParameterOptimizer:

    def __init__(self, sdf_func, target_points):
        self.sdf_func = sdf_func
        self.target = target_points

    def optimize(self, param_tensor, lr=1e-3, steps=200):
        opt = torch.optim.Adam([param_tensor], lr=lr)

        for _ in range(steps):
            opt.zero_grad()
            sdf_vals = self.sdf_func(self.target)
            loss = (sdf_vals**2).mean()
            loss.backward()
            opt.step()

        return param_tensor