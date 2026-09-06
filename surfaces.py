"""
surfaces.py
============

Surface-level geometry kernel for cad-agent.

This module defines parametric curves, surfaces, lofts, sweeps,
airfoils, spheroids, and adaptive tessellation hooks.

This is the foundation for:
- fighter jets
- sports equipment
- packaging
- industrial CAD
"""

import math
from abc import ABC, abstractmethod

import numpy as np

# ============================================================
# Utility math
# ============================================================

def lerp(a, b, t):
    return a * (1 - t) + b * t


def normalize(v):
    vector = np.asarray(v, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError("vector must contain three finite values")
    n = float(np.linalg.norm(vector))
    if n == 0:
        raise ValueError("zero-length vectors cannot be normalized")
    return vector / n


def rotation_matrix(axis, angle):
    axis = normalize(axis)
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)

    return np.array([
        [c + x*x*(1-c),     x*y*(1-c) - z*s, x*z*(1-c) + y*s],
        [y*x*(1-c) + z*s,   c + y*y*(1-c),   y*z*(1-c) - x*s],
        [z*x*(1-c) - y*s,   z*y*(1-c) + x*s, c + z*z*(1-c)]
    ])


# ============================================================
# Base Parametric Curve
# ============================================================

class Curve(ABC):
    @abstractmethod
    def point(self, t: float) -> np.ndarray:
        raise TypeError("Curve.point must be implemented by a concrete curve")

    def tangent(self, t: float) -> np.ndarray:
        dt = 1e-4
        return normalize(self.point(t + dt) - self.point(t))

    def sample(self, n=50):
        if not isinstance(n, int) or isinstance(n, bool) or n < 2:
            raise ValueError("curve sample count must be an integer of at least 2")
        return [self.point(i / (n - 1)) for i in range(n)]


# ============================================================
# Curve Types
# ============================================================

class Line(Curve):
    def __init__(self, p0, p1):
        self.p0 = np.asarray(p0, dtype=float)
        self.p1 = np.asarray(p1, dtype=float)
        if self.p0.shape != (3,) or self.p1.shape != (3,):
            raise ValueError("line endpoints must contain three coordinates")
        if not np.all(np.isfinite(self.p0)) or not np.all(np.isfinite(self.p1)):
            raise ValueError("line endpoints must be finite")

    def point(self, t):
        return lerp(self.p0, self.p1, t)


class Bezier(Curve):
    def __init__(self, control_points: list[tuple[float, float, float]]):
        if not control_points:
            raise ValueError("Bezier curves require at least one control point")
        self.ctrl = [np.asarray(p, dtype=float) for p in control_points]
        if any(point.shape != (3,) or not np.all(np.isfinite(point)) for point in self.ctrl):
            raise ValueError("Bezier control points must contain three finite coordinates")

    def point(self, t):
        pts = self.ctrl
        while len(pts) > 1:
            pts = [lerp(pts[i], pts[i+1], t) for i in range(len(pts)-1)]
        return pts[0]


class Circle(Curve):
    def __init__(self, radius=1.0, plane="xy"):
        if not isinstance(radius, (int, float)) or isinstance(radius, bool) or not math.isfinite(radius) or radius <= 0:
            raise ValueError("circle radius must be a positive finite number")
        if plane not in {"xy", "xz", "yz"}:
            raise ValueError("circle plane must be one of: xy, xz, yz")
        self.r = float(radius)
        self.plane = plane

    def point(self, t):
        a = 2 * math.pi * t
        if self.plane == "xy":
            return np.array([self.r * math.cos(a), self.r * math.sin(a), 0])
        if self.plane == "xz":
            return np.array([self.r * math.cos(a), 0, self.r * math.sin(a)])
        return np.array([0, self.r * math.cos(a), self.r * math.sin(a)])


# ============================================================
# Base Surface
# ============================================================

class Surface(ABC):
    @abstractmethod
    def point(self, u: float, v: float) -> np.ndarray:
        raise TypeError("Surface.point must be implemented by a concrete surface")

    def normal(self, u, v):
        du = 1e-4
        dv = 1e-4
        p = self.point(u, v)
        pu = self.point(u + du, v) - p
        pv = self.point(u, v + dv) - p
        return normalize(np.cross(pu, pv))

    def tessellate(self, nu=50, nv=50):
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 2 for value in (nu, nv)):
            raise ValueError("surface tessellation counts must be integers of at least 2")
        vertices = []
        faces = []

        for i in range(nu):
            for j in range(nv):
                u = i / (nu - 1)
                v = j / (nv - 1)
                vertices.append(self.point(u, v))

        def idx(i, j):
            return i * nv + j

        for i in range(nu - 1):
            for j in range(nv - 1):
                faces.append([
                    idx(i, j),
                    idx(i + 1, j),
                    idx(i + 1, j + 1)
                ])
                faces.append([
                    idx(i, j),
                    idx(i + 1, j + 1),
                    idx(i, j + 1)
                ])

        return vertices, faces


# ============================================================
# Ruled Surface
# ============================================================

class RuledSurface(Surface):
    def __init__(self, c1: Curve, c2: Curve):
        self.c1 = c1
        self.c2 = c2

    def point(self, u, v):
        return lerp(self.c1.point(u), self.c2.point(u), v)


# ============================================================
# Loft Surface
# ============================================================

class LoftSurface(Surface):
    def __init__(self, profiles: list[Curve]):
        self.profiles = profiles
        self.count = len(profiles)

    def point(self, u, v):
        idx = min(int(u * (self.count - 1)), self.count - 2)
        t = (u * (self.count - 1)) - idx

        p1 = self.profiles[idx].point(v)
        p2 = self.profiles[idx + 1].point(v)
        return lerp(p1, p2, t)


# ============================================================
# Sweep Surface
# ============================================================

class SweepSurface(Surface):
    def __init__(self, profile: Curve, path: Curve):
        self.profile = profile
        self.path = path

    def point(self, u, v):
        center = self.path.point(u)
        tangent = self.path.tangent(u)

        # create local frame
        up = np.array([0, 0, 1])
        if abs(np.dot(up, tangent)) > 0.9:
            up = np.array([0, 1, 0])

        side = normalize(np.cross(tangent, up))
        up = normalize(np.cross(side, tangent))

        p = self.profile.point(v)
        return center + side * p[0] + up * p[1]


# ============================================================
# Airfoil Surface
# ============================================================

class NACA4Airfoil(Curve):
    def __init__(self, m, p, t, chord=1.0):
        self.m = m
        self.p = p
        self.t = t
        self.c = chord

    def thickness(self, x):
        t = self.t
        return 5 * t * (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1015 * x**4
        )

    def camber(self, x):
        m, p = self.m, self.p
        if x < p:
            return m / (p**2) * (2*p*x - x*x)
        return m / ((1-p)**2) * ((1 - 2*p) + 2*p*x - x*x)

    def point(self, t):
        x = t * self.c
        yt = self.thickness(x / self.c)
        yc = self.camber(x / self.c)
        return np.array([x, yc + yt, 0])


class WingSurface(Surface):
    def __init__(self, airfoil: Curve, span=10.0, sweep=0.0):
        self.airfoil = airfoil
        self.span = span
        self.sweep = sweep

    def point(self, u, v):
        x, y, _ = self.airfoil.point(v)
        z = (u - 0.5) * self.span
        x += z * math.tan(self.sweep)
        return np.array([x, y, z])


# ============================================================
# Spheroids & Balls
# ============================================================

class SphereSurface(Surface):
    def __init__(self, r=1.0):
        self.r = r

    def point(self, u, v):
        theta = 2 * math.pi * u
        phi = math.pi * v
        return np.array([
            self.r * math.sin(phi) * math.cos(theta),
            self.r * math.sin(phi) * math.sin(theta),
            self.r * math.cos(phi)
        ])


class ProlateSpheroidSurface(Surface):
    def __init__(self, a, b):
        self.a = a  # long axis
        self.b = b  # short axis

    def point(self, u, v):
        theta = 2 * math.pi * u
        phi = math.pi * v
        return np.array([
            self.a * math.sin(phi) * math.cos(theta),
            self.b * math.sin(phi) * math.sin(theta),
            self.b * math.cos(phi)
        ])


# ============================================================
# Adaptive Tessellation Hook
# ============================================================

class AdaptiveSurfaceMesh:
    def __init__(self, surface: Surface):
        self.surface = surface

    def generate(self, target_polygons=1000):
        res = int(math.sqrt(target_polygons))
        verts, faces = self.surface.tessellate(res, res)
        return verts, faces


# ============================================================
# OpenSCAD Export
# ============================================================

def export_scad_polyhedron(vertices, faces, filename):
    with open(filename, "w") as f:
        f.write("polyhedron(\n")
        f.write("points=[\n")
        f.writelines(f"[{v[0]}, {v[1]}, {v[2]}],\n" for v in vertices)
        f.write("],\nfaces=[\n")
        f.writelines(f"{face},\n" for face in faces)
        f.write("]);\n")


# ============================================================
# High-level Factory
# ============================================================

class SurfaceFactory:
    @staticmethod
    def fighter_fuselage():
        profiles = [
            Circle(0.2),
            Circle(0.5),
            Circle(0.7),
            Circle(0.6),
            Circle(0.3)
        ]
        return LoftSurface(profiles)

    @staticmethod
    def football():
        return ProlateSpheroidSurface(a=1.0, b=0.6)
