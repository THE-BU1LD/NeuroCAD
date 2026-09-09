# universal_cad_core_v3.py
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from skimage import measure
import math


# =========================
# SDF GEOMETRY
# =========================
class SDF:

    def sphere(self, p, r=1.0):
        return np.linalg.norm(p, axis=-1) - r

    def grid(self, func, bounds=2.0, res=40):
        xs = np.linspace(-bounds, bounds, res)
        dx = xs[1] - xs[0]

        X, Y, Z = np.meshgrid(xs, xs, xs, indexing="ij")
        pts = np.stack([X, Y, Z], axis=-1)

        grid = func(pts).astype(np.float32)
        spacing = (dx, dx, dx)
        origin = np.array([-bounds, -bounds, -bounds])

        return grid, spacing, origin


# =========================
# GRADIENT + SAMPLING
# =========================
def sdf_gradient_grid(phi, spacing):
    gx = np.gradient(phi, spacing[0], axis=0)
    gy = np.gradient(phi, spacing[1], axis=1)
    gz = np.gradient(phi, spacing[2], axis=2)
    return gx, gy, gz


def sample_grid(grid, pts, origin, spacing):
    idx = (pts - origin) / spacing
    i0 = np.floor(idx).astype(int)
    d = idx - i0

    i0 = np.clip(i0, 0, np.array(grid.shape) - 2)

    x0, y0, z0 = i0[:, 0], i0[:, 1], i0[:, 2]
    x1, y1, z1 = x0 + 1, y0 + 1, z0 + 1

    c000 = grid[x0, y0, z0]
    c100 = grid[x1, y0, z0]
    c010 = grid[x0, y1, z0]
    c110 = grid[x1, y1, z0]
    c001 = grid[x0, y0, z1]
    c101 = grid[x1, y0, z1]
    c011 = grid[x0, y1, z1]
    c111 = grid[x1, y1, z1]

    xd, yd, zd = d[:, 0], d[:, 1], d[:, 2]

    c00 = c000 * (1 - xd) + c100 * xd
    c01 = c001 * (1 - xd) + c101 * xd
    c10 = c010 * (1 - xd) + c110 * xd
    c11 = c011 * (1 - xd) + c111 * xd

    c0 = c00 * (1 - yd) + c10 * yd
    c1 = c01 * (1 - yd) + c11 * yd

    return c0 * (1 - zd) + c1 * zd


def refine_vertices(verts, phi_grid, grad_grids, origin, spacing, iters=3):
    gx, gy, gz = grad_grids
    v = verts.copy()

    for _ in range(iters):
        phi = sample_grid(phi_grid, v, origin, spacing)

        g = np.stack([
            sample_grid(gx, v, origin, spacing),
            sample_grid(gy, v, origin, spacing),
            sample_grid(gz, v, origin, spacing)
        ], axis=1)

        g2 = np.sum(g * g, axis=1, keepdims=True) + 1e-12
        v = v - (phi[:, None] * g) / g2

    return v


def compute_vertex_normals(verts, grad_grids, origin, spacing):
    gx, gy, gz = grad_grids

    g = np.stack([
        sample_grid(gx, verts, origin, spacing),
        sample_grid(gy, verts, origin, spacing),
        sample_grid(gz, verts, origin, spacing)
    ], axis=1)

    n = g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-12)
    return n


# =========================
# MARCHING CUBES V3
# =========================
class MarchingCubes:

    def extract(
        self,
        grid,
        spacing=(1, 1, 1),
        origin=(0, 0, 0),
        level=0.0,
        refine=True,
        return_normals=True
    ):

        verts, faces, _, _ = measure.marching_cubes(
            grid,
            level=level,
            spacing=spacing
        )

        verts = verts + np.array(origin)

        if not refine and not return_normals:
            return verts, faces

        grad = sdf_gradient_grid(grid, spacing)

        if refine:
            verts = refine_vertices(
                verts,
                grid,
                grad,
                np.array(origin),
                np.array(spacing),
                iters=3
            )

        if return_normals:
            normals = compute_vertex_normals(
                verts,
                grad,
                np.array(origin),
                np.array(spacing)
            )
            return verts, faces, normals

        return verts, faces


# =========================
# FEM
# =========================
class TetFEM:

    def tetra_volume(self, a, b, c, d):
        return abs(np.dot(a - d, np.cross(b - d, c - d))) / 6.0

    def generate_tets(self, verts):
        n = len(verts)
        tets = []
        for i in range(0, n - 3, 4):
            tets.append([i, i + 1, i + 2, i + 3])
        return np.array(tets)

    def stiffness(self, verts, tets, E=200e9):
        K = 0.0
        for tet in tets:
            a, b, c, d = verts[tet]
            V = self.tetra_volume(a, b, c, d)
            K += E * V * 0.1
        return K


# =========================
# NEURAL CFD
# =========================
class NeuralCFD(nn.Module):

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 2)
        )

    def forward(self, x):
        return self.net(x)


class CFDTrainer:

    def __init__(self):
        self.model = NeuralCFD()
        self.opt = optim.Adam(self.model.parameters(), lr=1e-3)
        self.loss_fn = nn.MSELoss()

    def train(self, epochs=200):
        for _ in range(epochs):
            x = torch.rand(128, 3)

            area = x[:, 0] * 2.0
            vel = x[:, 1] * 100.0
            aoa = x[:, 2] * 0.3

            cl = 2 * math.pi * aoa
            cd = 0.02 + cl**2 / (math.pi * 6 * 0.8)

            inp = torch.stack([area, vel, aoa], dim=1)
            y = torch.stack([cl, cd], dim=1)

            pred = self.model(inp)
            loss = self.loss_fn(pred, y)

            self.opt.zero_grad()
            loss.backward()
            self.opt.step()

    def evaluate(self, area, vel, aoa):
        inp = torch.tensor([[area, vel, aoa]], dtype=torch.float32)
        cl, cd = self.model(inp)[0]

        rho = 1.225
        lift = 0.5 * rho * vel**2 * area * cl.item()
        drag = 0.5 * rho * vel**2 * area * cd.item()

        return lift, drag


# =========================
# TOPOLOGY
# =========================
class Topology:

    def genus(self, verts, faces):
        V = len(verts)
        F = len(faces)

        edges = set()
        for f in faces:
            edges.add(tuple(sorted((f[0], f[1]))))
            edges.add(tuple(sorted((f[1], f[2]))))
            edges.add(tuple(sorted((f[2], f[0]))))

        E = len(edges)
        chi = V - E + F

        return int(max(0, (2 - chi) // 2))


# =========================
# EXPORTERS
# =========================
class SCADExporter:

    def export(self, verts, faces, filename="output.scad"):
        with open(filename, "w") as f:
            f.write("polyhedron(points=[\n")
            for v in verts:
                f.write(f"[{v[0]}, {v[1]}, {v[2]}],\n")
            f.write("], faces=[\n")
            for face in faces:
                f.write(f"[{face[0]}, {face[1]}, {face[2]}],\n")
            f.write("]);\n")
        return filename


# =========================
# CORE
# =========================
class UniversalCADCoreV3:

    def __init__(self):
        self.sdf = SDF()
        self.mc = MarchingCubes()
        self.fem = TetFEM()
        self.cfd = CFDTrainer()
        self.topo = Topology()
        self.exporter = SCADExporter()

        self.cfd.train()

    def generate(self):

        grid, spacing, origin = self.sdf.grid(
            lambda p: self.sdf.sphere(p, 1.0),
            res=64
        )

        verts, faces, normals = self.mc.extract(
            grid,
            spacing=spacing,
            origin=origin
        )

        tets = self.fem.generate_tets(verts)
        stiffness = self.fem.stiffness(verts, tets)

        lift, drag = self.cfd.evaluate(area=1.0, vel=50, aoa=0.1)

        genus = self.topo.genus(verts, faces)

        file = self.exporter.export(verts, faces)

        return {
            "vertices": len(verts),
            "faces": len(faces),
            "stiffness": stiffness,
            "lift": lift,
            "drag": drag,
            "genus": genus,
            "file": file
        }


# =========================
# TEST
# =========================
if __name__ == "__main__":
    core = UniversalCADCoreV3()
    print(core.generate())
