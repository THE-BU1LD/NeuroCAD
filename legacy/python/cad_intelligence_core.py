import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from skimage import measure
import argparse
import time
import math
import os


class SDFPrimitives:
    def sphere(self, p, r=1.0, center=(0.0, 0.0, 0.0)):
        c = np.array(center)
        return np.linalg.norm(p - c, axis=-1) - r

    def box(self, p, size=(1.0, 1.0, 1.0), center=(0.0, 0.0, 0.0)):
        c = np.array(center)
        q = np.abs(p - c) - np.array(size)
        return np.linalg.norm(np.maximum(q, 0.0), axis=-1) + np.minimum(np.maximum(q[:, 0], np.maximum(q[:, 1], q[:, 2])), 0.0)

    def cylinder(self, p, r=1.0, h=1.0, center=(0.0, 0.0, 0.0)):
        c = np.array(center)
        d = p - c
        dxz = np.sqrt(d[:, 0] ** 2 + d[:, 2] ** 2) - r
        dy = np.abs(d[:, 1]) - h * 0.5
        q = np.stack([dxz, dy], axis=1)
        return np.minimum(np.maximum(q[:, 0], q[:, 1]), 0.0) + np.linalg.norm(np.maximum(q, 0.0), axis=1)


class SDFOperations:
    def union(self, a, b):
        return np.minimum(a, b)

    def intersection(self, a, b):
        return np.maximum(a, b)

    def difference(self, a, b):
        return np.maximum(a, -b)

    def smooth_union(self, a, b, k=0.2):
        h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
        return np.minimum(a, b) - k * h * (1.0 - h)


class GridSampler:
    def __init__(self, bounds=(-2, 2, -2, 2, -2, 2), resolution=128):
        self.bounds = bounds
        self.resolution = resolution

    def sample(self, sdf_fn):
        xmin, xmax, ymin, ymax, zmin, zmax = self.bounds
        n = self.resolution
        xs = np.linspace(xmin, xmax, n)
        ys = np.linspace(ymin, ymax, n)
        zs = np.linspace(zmin, zmax, n)
        dx = xs[1] - xs[0]
        dy = ys[1] - ys[0]
        dz = zs[1] - zs[0]
        grid = np.zeros((n, n, n), dtype=np.float32)
        for i in range(n):
            x = xs[i]
            for j in range(n):
                y = ys[j]
                pts = np.column_stack([np.full(n, x), np.full(n, y), zs])
                grid[i, j, :] = sdf_fn(pts)
        return grid, (dx, dy, dz), (xmin, ymin, zmin)


class MeshExtractor:
    def extract(self, grid, spacing, origin):
        verts, faces, _, _ = measure.marching_cubes(grid, level=0.0, spacing=spacing)
        verts = verts + np.array(origin)
        return verts, faces


class GradientRefiner:
    def gradient(self, phi, spacing):
        gx = np.gradient(phi, spacing[0], axis=0)
        gy = np.gradient(phi, spacing[1], axis=1)
        gz = np.gradient(phi, spacing[2], axis=2)
        return gx, gy, gz

    def sample(self, grid, pts, origin, spacing):
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

    def refine(self, verts, phi, grad, origin, spacing, iterations=3):
        gx, gy, gz = grad
        v = verts.copy()
        for _ in range(iterations):
            phi_vals = self.sample(phi, v, origin, spacing)
            g = np.stack([
                self.sample(gx, v, origin, spacing),
                self.sample(gy, v, origin, spacing),
                self.sample(gz, v, origin, spacing)
            ], axis=1)
            g2 = np.sum(g * g, axis=1, keepdims=True) + 1e-12
            v = v - (phi_vals[:, None] * g) / g2
        return v

    def normals(self, verts, grad, origin, spacing):
        gx, gy, gz = grad
        g = np.stack([
            self.sample(gx, verts, origin, spacing),
            self.sample(gy, verts, origin, spacing),
            self.sample(gz, verts, origin, spacing)
        ], axis=1)
        n = g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-12)
        return n


class FEMSolver:
    def tetra_volume(self, a, b, c, d):
        return abs(np.dot(a - d, np.cross(b - d, c - d))) / 6.0

    def generate(self, verts):
        n = len(verts)
        tets = []
        for i in range(0, n - 3, 4):
            tets.append([i, i + 1, i + 2, i + 3])
        return np.array(tets, dtype=int)

    def stiffness(self, verts, tets, E=200e9):
        K = 0.0
        for tet in tets:
            a, b, c, d = verts[tet]
            V = self.tetra_volume(a, b, c, d)
            K += E * V * 0.1
        return K


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
        self._train()

    def _train(self, epochs=200):
        for _ in range(epochs):
            x = torch.rand(256, 3)
            area = x[:, 0] * 2.0
            vel = x[:, 1] * 100.0
            aoa = x[:, 2] * 0.3
            cl = 2 * math.pi * aoa
            cd = 0.02 + cl ** 2 / (math.pi * 6 * 0.8)
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
        lift = 0.5 * rho * vel ** 2 * area * cl.item()
        drag = 0.5 * rho * vel ** 2 * area * cd.item()
        return lift, drag


class TopologyAnalyzer:
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


class OBJExporter:
    def export(self, verts, faces, normals=None, filename="output.obj"):
        with open(filename, "w") as f:
            for v in verts:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            if normals is not None:
                for n in normals:
                    f.write(f"vn {n[0]} {n[1]} {n[2]}\n")
            for face in faces:
                if normals is not None:
                    f.write(f"f {face[0]+1}//{face[0]+1} {face[1]+1}//{face[1]+1} {face[2]+1}//{face[2]+1}\n")
                else:
                    f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
        return filename


class UniversalCADCore:
    def __init__(self, bounds=(-2, 2, -2, 2, -2, 2), resolution=128):
        self.primitives = SDFPrimitives()
        self.ops = SDFOperations()
        self.sampler = GridSampler(bounds, resolution)
        self.extractor = MeshExtractor()
        self.refiner = GradientRefiner()
        self.fem = FEMSolver()
        self.cfd = CFDTrainer()
        self.topology = TopologyAnalyzer()
        self.exporter = OBJExporter()

    def build_sdf(self, shape="sphere"):
        if shape == "sphere":
            return lambda p: self.primitives.sphere(p, 1.0)
        if shape == "box":
            return lambda p: self.primitives.box(p, (1.0, 1.0, 1.0))
        if shape == "cylinder":
            return lambda p: self.primitives.cylinder(p, 1.0, 2.0)
        return lambda p: self.primitives.sphere(p, 1.0)

    def generate(self, shape="sphere", refine=True):
        sdf_fn = self.build_sdf(shape)
        grid, spacing, origin = self.sampler.sample(sdf_fn)
        verts, faces = self.extractor.extract(grid, spacing, origin)
        grad = self.refiner.gradient(grid, spacing)
        if refine:
            verts = self.refiner.refine(verts, grid, grad, np.array(origin), np.array(spacing))
        normals = self.refiner.normals(verts, grad, np.array(origin), np.array(spacing))
        tets = self.fem.generate(verts)
        stiffness = self.fem.stiffness(verts, tets)
        lift, drag = self.cfd.evaluate(1.0, 50.0, 0.1)
        genus = self.topology.genus(verts, faces)
        file = self.exporter.export(verts, faces, normals)
        return {
            "vertices": len(verts),
            "faces": len(faces),
            "stiffness": stiffness,
            "lift": lift,
            "drag": drag,
            "genus": genus,
            "file": file
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shape", type=str, default="sphere")
    parser.add_argument("--res", type=int, default=128)
    parser.add_argument("--bounds", type=float, nargs=6, default=[-2, 2, -2, 2, -2, 2])
    args = parser.parse_args()
    start = time.time()
    core = UniversalCADCore(bounds=tuple(args.bounds), resolution=args.res)
    result = core.generate(shape=args.shape)
    end = time.time()
    result["runtime_seconds"] = end - start
    print(result)


if __name__ == "__main__":
    main()
