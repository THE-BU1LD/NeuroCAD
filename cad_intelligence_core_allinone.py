# cad_intelligence_core_allinone.py
# FINAL — stable API for sword + CAD kernel

import math
import struct
import numpy as np
from dataclasses import dataclass
from typing import Callable

from cad_intelligence_core import DiffGeometry
from universal_cad_core import CFDTrainer, TetFEM, Topology


# ============================================================
# SDF CORE
# ============================================================

class SDF:
    def __init__(self, fn: Callable[[np.ndarray], np.ndarray] | None = None):
        self.fn = fn

    def __call__(self, pts: np.ndarray) -> np.ndarray:
        pts = np.asarray(pts)
        if self.fn is None:
            raise ValueError("SDF function not defined")
        if pts.ndim == 1:
            pts = pts[None, :]
            return self.fn(pts)[0]
        return self.fn(pts)

    # ---------------- primitives ----------------

    @staticmethod
    def sphere(p, r=1.0):
        return np.linalg.norm(p, axis=-1) - r

    # ---------------- grid sampling ----------------

    def grid(self, fn, bounds=1.0, res=64):
        if isinstance(bounds, (int, float)):
            xmin = ymin = zmin = -bounds
            xmax = ymax = zmax = bounds
        else:
            xmin, xmax = bounds
            ymin, ymax = bounds
            zmin, zmax = bounds

        xs = np.linspace(xmin, xmax, res)
        ys = np.linspace(ymin, ymax, res)
        zs = np.linspace(zmin, zmax, res)

        dx = (xmax - xmin) / (res - 1)
        dy = (ymax - ymin) / (res - 1)
        dz = (zmax - zmin) / (res - 1)

        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
        pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=-1)

        vals = fn(pts).reshape(res, res, res).astype(np.float32)

        origin = (xmin, ymin, zmin)
        spacing = (dx, dy, dz)

        return vals, spacing, origin


# ============================================================
# NORMALS
# ============================================================

def compute_vertex_normals(verts, faces):
    normals = np.zeros_like(verts)
    tris = verts[faces]
    fn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    for i, f in enumerate(faces):
        normals[f] += fn[i]
    n = np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
    return normals / n


# ============================================================
# MARCHING CUBES
# ============================================================

from skimage import measure


class MarchingCubes:

    def __init__(self, level=0.0):
        self.level = level

    def extract(
        self,
        grid,
        spacing=(1, 1, 1),
        origin=(0, 0, 0),
        refine=True,
        return_normals=True,
    ):

        verts, faces, _, _ = measure.marching_cubes(
            grid,
            level=self.level,
            spacing=spacing
        )

        verts = verts + np.array(origin)

        if not refine and not return_normals:
            return verts.astype(np.float32), faces.astype(np.int32)

        gx = np.gradient(grid, spacing[0], axis=0)
        gy = np.gradient(grid, spacing[1], axis=1)
        gz = np.gradient(grid, spacing[2], axis=2)

        def sample(grid, pts):
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

        verts_ref = verts.copy()

        if refine:
            for _ in range(3):
                phi = sample(grid, verts_ref)
                g = np.stack([
                    sample(gx, verts_ref),
                    sample(gy, verts_ref),
                    sample(gz, verts_ref)
                ], axis=1)

                g2 = np.sum(g * g, axis=1, keepdims=True) + 1e-12
                verts_ref -= (phi[:, None] * g) / g2

        if return_normals:
            n = np.stack([
                sample(gx, verts_ref),
                sample(gy, verts_ref),
                sample(gz, verts_ref)
            ], axis=1)
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            return verts_ref.astype(np.float32), faces.astype(np.int32), n.astype(np.float32)

        return verts_ref.astype(np.float32), faces.astype(np.int32)


# ============================================================
# EXPORTERS
# ============================================================

class SCADExporter:
    def export(self, verts, faces, filename="output.scad"):
        with open(filename, "w") as f:
            f.write("polyhedron(points=[\n")
            for v in verts:
                f.write(f"[{v[0]},{v[1]},{v[2]}],\n")
            f.write("], faces=[\n")
            for tri in faces:
                f.write(f"[{tri[0]},{tri[1]},{tri[2]}],\n")
            f.write("]);\n")
        return filename


class STEPExporter:
    def export(self, verts, faces, filename="output.step"):
        with open(filename, "w") as f:
            f.write("ISO-10303-21;\n")
            f.write("/* Mesh placeholder STEP */\n")
            f.write("END-ISO-10303-21;\n")
        return filename


# ============================================================
# MODEL
# ============================================================

@dataclass
class ImplicitModel:
    sdf: Callable
    bounds: float = 1.0
    res: int = 64

    def mesh(self):
        grid, spacing, origin = SDF().grid(self.sdf, bounds=self.bounds, res=self.res)
        mc = MarchingCubes()
        return mc.extract(grid, spacing, origin)


# ============================================================
# PUBLIC KERNEL
# ============================================================

class UniversalCADCoreV3:

    def __init__(self):
        self.sdf = SDF()
        self.mc = MarchingCubes()
        self.fem = TetFEM()
        self.cfd = CFDTrainer()
        self.diff = DiffGeometry()
        self.topo = Topology()
        self.exporter = SCADExporter()

        self.cfd.train()

    def generate(self):

        grid, spacing, origin = self.sdf.grid(
            lambda p: SDF.sphere(p, 1.0),
            bounds=2.0,
            res=40
        )

        verts, faces, _ = self.mc.extract(
            grid,
            spacing=spacing,
            origin=origin,
            refine=True,
            return_normals=True
        )

        tets = self.fem.generate_tets(verts)
        stiffness = self.fem.stiffness(verts, tets)

        lift, drag = self.cfd.evaluate(area=1.0, vel=50, aoa=0.1)
        u, v = self.diff.optimize_param()
        genus = self.topo.genus(verts, faces)

        file = self.exporter.export(verts, faces)

        return {
            "vertices": len(verts),
            "faces": len(faces),
            "stiffness": stiffness,
            "lift": lift,
            "drag": drag,
            "optimized_params": (u, v),
            "genus": genus,
            "file": file
        }
