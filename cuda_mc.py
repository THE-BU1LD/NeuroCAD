import numpy as np
import torch
from skimage import measure
from device import device


class CUDAMarchingCubes:

    def extract(self, sdf_model, res=140, bounds=2.0):
        lin = torch.linspace(-bounds, bounds, res, device=device)
        X, Y, Z = torch.meshgrid(lin, lin, lin, indexing="ij")
        pts = torch.stack([X, Y, Z], dim=-1)

        with torch.no_grad():
            field = sdf_model(pts).cpu().numpy()

        verts, faces, _, _ = measure.marching_cubes(field, level=0.0)

        scale = (2 * bounds) / (res - 1)
        verts = verts * scale - bounds

        return verts.astype(np.float32), faces.astype(np.int32)
