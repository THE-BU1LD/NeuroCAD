import torch
import numpy as np


# ============================================================
# PRIMITIVES
# ============================================================

class SDFPrimitives:

    @staticmethod
    def sphere(p, radius=0.5):
        return torch.linalg.norm(p, dim=-1) - radius

    @staticmethod
    def box(p, size):
        size = torch.tensor(size, device=p.device)
        q = torch.abs(p) - size
        return torch.linalg.norm(torch.clamp(q, min=0), dim=-1) + torch.clamp(q.max(dim=-1).values, max=0)

    @staticmethod
    def cylinder(p, radius=0.3, height=1.0):
        d = torch.stack([
            torch.linalg.norm(p[..., :2], dim=-1) - radius,
            torch.abs(p[..., 2]) - height/2
        ], dim=-1)
        return torch.clamp(d.max(dim=-1).values, min=0) + torch.linalg.norm(torch.clamp(d, min=0), dim=-1)

    @staticmethod
    def torus(p, R=0.6, r=0.2):
        q = torch.stack([
            torch.linalg.norm(p[..., :2], dim=-1) - R,
            p[..., 2]
        ], dim=-1)
        return torch.linalg.norm(q, dim=-1) - r


# ============================================================
# BOOLEAN OPS
# ============================================================

class SDFOps:

    @staticmethod
    def union(a, b):
        return torch.minimum(a, b)

    @staticmethod
    def intersection(a, b):
        return torch.maximum(a, b)

    @staticmethod
    def difference(a, b):
        return torch.maximum(a, -b)

    @staticmethod
    def smooth_union(a, b, k=0.2):
        h = torch.clamp(0.5 + 0.5*(b-a)/k, 0, 1)
        return torch.lerp(b, a, h) - k*h*(1-h)


# ============================================================
# CONNECTIONS
# ============================================================

class Connections:

    @staticmethod
    def peg(p, radius=0.1, height=0.3):
        return SDFPrimitives.cylinder(p, radius, height)

    @staticmethod
    def socket(p, radius=0.11, depth=0.32):
        return -SDFPrimitives.cylinder(p, radius, depth)

    @staticmethod
    def hinge(p, r_outer=0.2, r_inner=0.15):
        outer = SDFPrimitives.cylinder(p, r_outer, 0.2)
        inner = SDFPrimitives.cylinder(p, r_inner, 0.22)
        return SDFOps.difference(outer, inner)
