import torch
import numpy as np


class GridSampler:

    def __init__(self, sdf, bounds=1.2, res=96, device="cpu"):
        self.sdf = sdf
        self.bounds = bounds
        self.res = res
        self.device = device

    def sample(self):
        xs = np.linspace(-self.bounds, self.bounds, self.res)
        grid = np.stack(np.meshgrid(xs, xs, xs, indexing="ij"), -1)
        pts = torch.tensor(grid, device=self.device).float()

        phi = self.sdf(pts).cpu().numpy()
        spacing = (2*self.bounds)/(self.res-1)
        origin = np.array([-self.bounds]*3)
        return phi, spacing, origin


class OctreeSampler:

    def __init__(self, sdf, bounds=1.2, depth=6, device="cpu"):
        self.sdf = sdf
        self.bounds = bounds
        self.depth = depth
        self.device = device

    def _grad_mag(self, p, eps=1e-3):
        p = torch.tensor(p, device=self.device).float()
        offsets = torch.eye(3, device=self.device)*eps

        g=[]
        for i in range(3):
            f1 = self.sdf((p+offsets[i]).unsqueeze(0))[0]
            f2 = self.sdf((p-offsets[i]).unsqueeze(0))[0]
            g.append((f1-f2)/(2*eps))

        return torch.linalg.norm(torch.stack(g)).item()

    def _subdivide(self, center, size, level, cells):
        c = torch.tensor(center, device=self.device).float()
        d = self.sdf(c.unsqueeze(0)).item()

        if abs(d) > size:
            return

        curv = self._grad_mag(center)

        if level==0 or curv < 0.4:
            cells.append((center,size))
            return

        h=size/4
        for dx in (-h,h):
            for dy in (-h,h):
                for dz in (-h,h):
                    self._subdivide(center+np.array([dx,dy,dz]), size/2, level-1, cells)

    def sample(self, res):
        cells=[]
        self._subdivide(np.array([0,0,0]), self.bounds*2, self.depth, cells)

        xs = np.linspace(-self.bounds, self.bounds, res)
        grid = np.stack(np.meshgrid(xs,xs,xs,indexing="ij"),-1)
        pts = torch.tensor(grid, device=self.device).float()

        phi = self.sdf(pts).cpu().numpy()
        spacing = (2*self.bounds)/(res-1)
        origin = np.array([-self.bounds]*3)
        return phi, spacing, origin
