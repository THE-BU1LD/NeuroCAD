# ============================================================
# CAD MASTER KERNEL V3
# GPU + Implicit SDF + Neural + Decimation + Clean API
# ============================================================

import numpy as np
import torch
import torch.nn as nn
import trimesh
from skimage import measure

# ============================================================
# DEVICE
# ============================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", DEVICE)


# ============================================================
# UTILITIES
# ============================================================

def normalize(v):
    return v / (np.linalg.norm(v) + 1e-8)


# ============================================================
# SDF PRIMITIVES
# ============================================================

class SDFPrimitives:

    def sphere(self, p, r):
        return torch.linalg.norm(p, dim=-1) - r

    def box(self, p, size):
        size = torch.tensor(size, device=p.device, dtype=p.dtype)
        q = torch.abs(p) - size
        return torch.linalg.norm(torch.clamp(q, min=0), dim=-1) + \
               torch.clamp(q.max(dim=-1).values, max=0)

    def cylinder(self, p, r, h):
        d = torch.stack([
            torch.linalg.norm(p[..., :2], dim=-1) - r,
            torch.abs(p[..., 2]) - h / 2
        ], dim=-1)

        return torch.minimum(
            torch.maximum(d[..., 0], d[..., 1]),
            torch.zeros_like(d[..., 0])
        ) + torch.linalg.norm(torch.clamp(d, min=0), dim=-1)

    def torus(self, p, R, r):
        q = torch.stack([
            torch.linalg.norm(p[..., :2], dim=-1) - R,
            p[..., 2]
        ], dim=-1)
        return torch.linalg.norm(q, dim=-1) - r


# ============================================================
# BOOLEAN OPS
# ============================================================

def sdf_union(a, b):
    return torch.minimum(a, b)

def sdf_subtract(a, b):
    return torch.maximum(a, -b)

def sdf_intersect(a, b):
    return torch.maximum(a, b)

def sdf_smooth_union(a, b, k):
    h = torch.clamp(0.5 + 0.5*(b-a)/k, 0, 1)
    return torch.lerp(b, a, h) - k*h*(1-h)


# ============================================================
# SDF GRAPH
# ============================================================

class SDFGraph:

    def __init__(self):
        self.ops = []

    def add(self, sdf):
        self.ops.append(("union", sdf))

    def subtract(self, sdf):
        self.ops.append(("subtract", sdf))

    def intersect(self, sdf):
        self.ops.append(("intersect", sdf))

    def smooth_add(self, sdf, k=0.2):
        self.ops.append(("smooth", sdf, k))

    def build(self):

        def composed(p):

            result = None

            for op in self.ops:

                if op[0] == "smooth":
                    _, sdf_func, k = op
                else:
                    _, sdf_func = op
                    k = None

                value = sdf_func(p)

                if result is None:
                    result = value
                else:
                    if op[0] == "union":
                        result = sdf_union(result, value)
                    elif op[0] == "subtract":
                        result = sdf_subtract(result, value)
                    elif op[0] == "intersect":
                        result = sdf_intersect(result, value)
                    elif op[0] == "smooth":
                        result = sdf_smooth_union(result, value, k)

            return result

        return composed


# ============================================================
# NEURAL REFINER
# ============================================================

class NeuralSDF(nn.Module):

    def __init__(self, hidden=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3, hidden),
            nn.SiLU(),
            nn.Linear(hidden, hidden),
            nn.SiLU(),
            nn.Linear(hidden, 1)
        )

    def forward(self, x):
        return self.net(x)

    def wrap(self, sdf_func):

        def refined(p):
            base = sdf_func(p)
            correction = self.forward(p).squeeze(-1)
            return base + 0.02 * correction

        return refined


# ============================================================
# KERNEL
# ============================================================

class CADKernel:

    def __init__(self, resolution=128, neural=False):

        self.resolution = resolution
        self.prim = SDFPrimitives()
        self.neural_enabled = neural

        if neural:
            self.neural = NeuralSDF().to(DEVICE)

    def new_graph(self):
        return SDFGraph()

    # --------------------------------------------------------

    def primitive(self, shape, **params):

        if shape == "sphere":
            return lambda p: self.prim.sphere(p, params.get("r", 0.5))

        if shape == "box":
            return lambda p: self.prim.box(p, params.get("size", [0.5]*3))

        if shape == "cylinder":
            return lambda p: self.prim.cylinder(
                p,
                params.get("r", 0.3),
                params.get("h", 1.0)
            )

        if shape == "torus":
            return lambda p: self.prim.torus(
                p,
                params.get("R", 0.5),
                params.get("r", 0.1)
            )

        raise ValueError("Unknown primitive")

    # --------------------------------------------------------

    def build(self, graph, bounds=1.2, decimate=0.0):

        sdf = graph.build()

        if self.neural_enabled:
            sdf = self.neural.wrap(sdf)

        # sample grid
        xs = torch.linspace(-bounds, bounds, self.resolution, device=DEVICE)
        grid = torch.stack(torch.meshgrid(xs, xs, xs, indexing="ij"), -1)
        flat = grid.reshape(-1, 3)

        with torch.no_grad():
            sdf_vals = sdf(flat).cpu().numpy()

        volume = sdf_vals.reshape(
            self.resolution,
            self.resolution,
            self.resolution
        )

        verts, faces, normals, _ = measure.marching_cubes(
            volume,
            level=0.0
        )

        verts = (verts / self.resolution) * (2*bounds) - bounds

        mesh = {
            "verts": verts,
            "faces": faces,
            "normals": normals
        }

        if decimate > 0.0:
            mesh = self._decimate(mesh, decimate)

        return mesh

    # --------------------------------------------------------

    def _decimate(self, mesh, reduction):

        tm = trimesh.Trimesh(
            vertices=mesh["verts"],
            faces=mesh["faces"]
        )

        try:
            tm = tm.simplify_quadric_decimation(
                target_reduction=reduction
            )
        except:
            print("Decimation skipped (dependency missing)")

        return {
            "verts": tm.vertices,
            "faces": tm.faces,
            "normals": tm.vertex_normals
        }

    # --------------------------------------------------------

    def export_stl(self, mesh, path):
        tm = trimesh.Trimesh(mesh["verts"], mesh["faces"])
        tm.export(path)

    def export_scad(self, mesh, path):

        with open(path, "w") as f:
            f.write("polyhedron(points=[\n")
            for v in mesh["verts"]:
                f.write(f"[{v[0]}, {v[1]}, {v[2]}],\n")
            f.write("], faces=[\n")
            for tri in mesh["faces"]:
                f.write(f"[{tri[0]}, {tri[1]}, {tri[2]}],\n")
            f.write("]);")