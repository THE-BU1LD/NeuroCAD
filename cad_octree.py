# cad_octree.py

import torch
import numpy as np
import trimesh
from skimage import measure

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class AdaptiveOctreeDC:

    def __init__(self, sdf, base_res=64, max_depth=3, bounds=1.0):
        self.sdf = sdf
        self.base_res = base_res
        self.max_depth = max_depth
        self.bounds = bounds

    def extract(self):
        xs = torch.linspace(-self.bounds, self.bounds, self.base_res, device=DEVICE)
        grid = torch.stack(torch.meshgrid(xs, xs, xs, indexing="ij"), -1)
        flat = grid.reshape(-1, 3)

        with torch.no_grad():
            vals = self.sdf(flat).cpu().numpy()

        vals = vals.reshape(self.base_res, self.base_res, self.base_res)

        verts, faces, normals, _ = measure.marching_cubes(
            vals,
            level=0.0,
            spacing=(2*self.bounds/self.base_res,) * 3
        )

        verts += np.array([-self.bounds]*3)

        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        mesh = mesh.simplify_quadratic_decimation(len(mesh.faces)//2)

        return mesh.vertices, mesh.faces, mesh.vertex_normals