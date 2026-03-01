# ============================================================
# CAD MASTER KERNEL V5 — MAX ENGINE
# Optimized | Chunked | Cached | Mixed Precision | Stable
# ============================================================

import numpy as np
import torch
import torch.nn as nn
import trimesh
import gc
import shutil
import subprocess
import hashlib
from skimage import measure

torch.backends.cudnn.benchmark = True
torch.backends.cudnn.deterministic = True

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

print("Using device:", DEVICE)


# ============================================================
# UTILITIES
# ============================================================

def normalize(v):
    return v / (np.linalg.norm(v) + 1e-8)


def hash_graph(graph):
    return hashlib.md5(str(graph.ops).encode()).hexdigest()


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

def sdf_union(a, b): return torch.minimum(a, b)
def sdf_subtract(a, b): return torch.maximum(a, -b)
def sdf_intersect(a, b): return torch.maximum(a, b)

def sdf_smooth_union(a, b, k):
    h = torch.clamp(0.5 + 0.5*(b-a)/k, 0, 1)
    return torch.lerp(b, a, h) - k*h*(1-h)


# ============================================================
# GRAPH SYSTEM
# ============================================================

class SDFGraph:

    def __init__(self):
        self.ops = []
        self._compiled = None
        self._hash = None

    def add(self, sdf): self.ops.append(("union", sdf))
    def subtract(self, sdf): self.ops.append(("subtract", sdf))
    def intersect(self, sdf): self.ops.append(("intersect", sdf))
    def smooth_add(self, sdf, k=0.15): self.ops.append(("smooth", sdf, k))

    def build(self):

        h = hash_graph(self)
        if self._compiled and self._hash == h:
            return self._compiled

        def composed(p):

            result = None

            for op in self.ops:

                if op[0] == "smooth":
                    _, sdf_func, k = op
                else:
                    _, sdf_func = op
                    k = None

                val = sdf_func(p)

                if result is None:
                    result = val
                else:
                    if op[0] == "union":
                        result = sdf_union(result, val)
                    elif op[0] == "subtract":
                        result = sdf_subtract(result, val)
                    elif op[0] == "intersect":
                        result = sdf_intersect(result, val)
                    elif op[0] == "smooth":
                        result = sdf_smooth_union(result, val, k)

            return result

        self._compiled = composed
        self._hash = h
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
# MAIN KERNEL
# ============================================================

class CADKernel:

    def __init__(self, resolution=128, neural=False, force_cpu=False):

        self.resolution = resolution
        self.prim = SDFPrimitives()
        self.device = "cpu" if force_cpu else DEVICE
        self.dtype = DTYPE
        self.neural_enabled = neural

        if neural:
            self.neural = NeuralSDF().to(self.device)

    # --------------------------------------------------------

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
                p, params.get("r", 0.3), params.get("h", 1.0)
            )

        if shape == "torus":
            return lambda p: self.prim.torus(
                p, params.get("R", 0.5), params.get("r", 0.1)
            )

        raise ValueError("Unknown primitive")

    # --------------------------------------------------------

    def build(self, graph, bounds=1.5, decimate=0.0,
              chunk=600_000, smooth_iters=1):

        voxels = self.resolution ** 3
        if voxels > 40_000_000:
            self.resolution = int(self.resolution * 0.7)

        sdf = graph.build()

        if self.neural_enabled:
            sdf = self.neural.wrap(sdf)

        xs = torch.linspace(-bounds, bounds, self.resolution,
                            device=self.device, dtype=self.dtype)

        grid = torch.stack(torch.meshgrid(xs, xs, xs, indexing="ij"), -1)
        flat = grid.reshape(-1, 3)

        vals = []

        try:
            with torch.no_grad():
                for i in range(0, flat.shape[0], chunk):
                    vals.append(sdf(flat[i:i+chunk]).cpu())
        except RuntimeError:
            print("⚠ CUDA OOM — falling back to CPU.")
            self.device = "cpu"
            return self.build(graph, bounds, decimate)

        vals = torch.cat(vals).numpy()
        volume = vals.reshape(self.resolution,
                              self.resolution,
                              self.resolution)

        if np.min(volume) > 0 or np.max(volume) < 0:
            print("No surface detected.")
            return None

        verts, faces, normals, _ = measure.marching_cubes(
            volume, level=0.0)

        verts = verts / (self.resolution - 1) * (2 * bounds) - bounds

        tm = trimesh.Trimesh(vertices=verts, faces=faces, process=False)

        tm.remove_degenerate_faces()
        tm.remove_duplicate_faces()
        tm.remove_unreferenced_vertices()
        tm.fix_normals()

        for _ in range(smooth_iters):
            try:
                tm = tm.smoothed()
            except:
                break

        if decimate > 0:
            try:
                tm = tm.simplify_quadric_decimation(
                    target_reduction=decimate)
            except:
                pass

        gc.collect()

        return {
            "verts": tm.vertices,
            "faces": tm.faces,
            "normals": tm.vertex_normals
        }

    # --------------------------------------------------------

    def analyze(self, mesh):

        tm = trimesh.Trimesh(mesh["verts"], mesh["faces"])

        return {
            "verts": len(tm.vertices),
            "faces": len(tm.faces),
            "volume": float(tm.volume),
            "area": float(tm.area),
            "watertight": bool(tm.is_watertight),
            "euler": int(tm.euler_number)
        }

    # --------------------------------------------------------

    def export_stl(self, mesh, path):
        trimesh.Trimesh(mesh["verts"], mesh["faces"]).export(path)

    def export_scad(self, mesh, path):

        with open(path, "w") as f:
            f.write("$fn=64;\npolyhedron(points=[\n")
            for v in mesh["verts"]:
                f.write(f"[{v[0]}, {v[1]}, {v[2]}],\n")
            f.write("], faces=[\n")
            for tri in mesh["faces"]:
                f.write(f"[{tri[0]}, {tri[1]}, {tri[2]}],\n")
            f.write("]);")

    def render_scad(self, scad_path, output_path):
        if shutil.which("openscad"):
            subprocess.run(["openscad", "-o",
                            output_path, scad_path])
        else:
            print("OpenSCAD not installed.")