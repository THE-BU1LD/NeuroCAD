"""
resolution_engine.py
High-performance adaptive refinement engine for cad-agent.
Optimized for macOS + 2GB RAM limit.
"""

import numpy as np


# ============================================================
# Mesh (Numpy-backed, memory efficient)
# ============================================================

class Mesh:
    def __init__(self, vertices=None, faces=None):
        self.vertices = (
            np.asarray(vertices, dtype=np.float32)
            if vertices is not None
            else np.zeros((0, 3), dtype=np.float32)
        )

        self.faces = (
            np.asarray(faces, dtype=np.int32)
            if faces is not None
            else np.zeros((0, 3), dtype=np.int32)
        )

    @property
    def poly_count(self):
        return self.faces.shape[0]

    @property
    def vert_count(self):
        return self.vertices.shape[0]

    def copy(self):
        return Mesh(self.vertices.copy(), self.faces.copy())


# ============================================================
# Vectorized Geometry
# ============================================================

def compute_face_normals(vertices, faces):
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    return np.cross(v1 - v0, v2 - v0)


def compute_face_area(normals):
    return np.linalg.norm(normals, axis=1) * 0.5


def compute_face_curvature(normals):
    return np.linalg.norm(normals, axis=1)


# ============================================================
# Adaptive Subdivider
# ============================================================

class Subdivider:
    def __init__(self, curvature_weight=1.0, area_weight=0.25):
        self.curvature_weight = curvature_weight
        self.area_weight = area_weight

    def score_faces(self, mesh: Mesh):
        normals = compute_face_normals(mesh.vertices, mesh.faces)
        area = compute_face_area(normals)
        curvature = compute_face_curvature(normals)
        return self.curvature_weight * curvature + self.area_weight * area

    def subdivide(self, mesh: Mesh, face_indices):
        vertices = mesh.vertices
        faces = mesh.faces

        edge_cache = {}
        new_vertices = vertices.tolist()
        new_faces = []

        def midpoint_index(i, j):
            key = (i, j) if i < j else (j, i)
            if key in edge_cache:
                return edge_cache[key]

            v = (vertices[i] + vertices[j]) * 0.5
            idx = len(new_vertices)
            new_vertices.append(v)
            edge_cache[key] = idx
            return idx

        split_set = set(face_indices)

        for fi, face in enumerate(faces):

            if fi not in split_set:
                new_faces.append(face.tolist())
                continue

            i0, i1, i2 = face

            a = midpoint_index(i0, i1)
            b = midpoint_index(i1, i2)
            c = midpoint_index(i2, i0)

            new_faces.extend([
                [i0, a, c],
                [a, i1, b],
                [c, b, i2],
                [a, b, c]
            ])

        return Mesh(
            np.asarray(new_vertices, dtype=np.float32),
            np.asarray(new_faces, dtype=np.int32)
        )


# ============================================================
# Resolution Engine (Scalable)
# ============================================================

class ResolutionEngine:
    def __init__(
        self,
        target_polygons=100000,
        max_iterations=6,
        curvature_threshold=0.01,
        memory_limit_mb=1800
    ):
        self.target = target_polygons
        self.max_iter = max_iterations
        self.curvature_threshold = curvature_threshold
        self.memory_limit_mb = memory_limit_mb

    def _memory_estimate(self, mesh: Mesh):
        v_mem = mesh.vertices.nbytes
        f_mem = mesh.faces.nbytes
        return (v_mem + f_mem) / (1024 ** 2)

    def escalate(self, mesh: Mesh):

        subdivider = Subdivider()
        current = mesh.copy()

        for _ in range(self.max_iter):

            if current.poly_count >= self.target:
                break

            if self._memory_estimate(current) > self.memory_limit_mb:
                break

            scores = subdivider.score_faces(current)

            remaining = self.target - current.poly_count
            if remaining <= 0:
                break

            split_count = min(len(scores), max(1, remaining // 3))

            important = np.argsort(scores)[-split_count:]
            important = [
                idx for idx in important
                if scores[idx] > self.curvature_threshold
            ]

            if not important:
                break

            current = subdivider.subdivide(current, important)

        return current


# ============================================================
# LOD Generator (Efficient)
# ============================================================

class LODGenerator:
    def __init__(self, levels=(2000, 20000, 200000)):
        self.levels = sorted(levels)

    def generate(self, base_mesh: Mesh):
        lods = {}
        current = base_mesh.copy()

        for level in self.levels:
            engine = ResolutionEngine(target_polygons=level)
            current = engine.escalate(current)
            lods[level] = current.copy()

        return lods


# ============================================================
# Export STL (Fast, stable)
# ============================================================

def export_stl(mesh: Mesh, filename):
    with open(filename, "w") as f:
        f.write("solid cad_agent\n")

        normals = compute_face_normals(mesh.vertices, mesh.faces)
        norms = np.linalg.norm(normals, axis=1) + 1e-9
        normals = normals / norms[:, None]

        for i, face in enumerate(mesh.faces):
            v0, v1, v2 = mesh.vertices[face]

            n = normals[i]
            f.write(f"facet normal {n[0]} {n[1]} {n[2]}\n")
            f.write(" outer loop\n")
            f.write(f"  vertex {v0[0]} {v0[1]} {v0[2]}\n")
            f.write(f"  vertex {v1[0]} {v1[1]} {v1[2]}\n")
            f.write(f"  vertex {v2[0]} {v2[1]} {v2[2]}\n")
            f.write(" endloop\n")
            f.write("endfacet\n")

        f.write("endsolid cad_agent\n")


# ============================================================
# Stress Test
# ============================================================

if __name__ == "__main__":

    def unit_sphere(res=12):
        verts = []
        faces = []

        for i in range(res + 1):
            theta = np.pi * i / res
            for j in range(res):
                phi = 2 * np.pi * j / res
                x = np.sin(theta) * np.cos(phi)
                y = np.sin(theta) * np.sin(phi)
                z = np.cos(theta)
                verts.append([x, y, z])

        verts = np.array(verts, dtype=np.float32)

        for i in range(res):
            for j in range(res - 1):
                a = i * res + j
                b = a + res
                faces.append([a, b, a + 1])
                faces.append([a + 1, b, b + 1])

        return Mesh(verts, np.array(faces, dtype=np.int32))

    base = unit_sphere(16)

    engine = ResolutionEngine(target_polygons=200000)
    refined = engine.escalate(base)

    print("Vertices:", refined.vert_count)
    print("Polygons:", refined.poly_count)

    export_stl(refined, "high_res_sphere.stl")
