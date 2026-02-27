# cad_meshing.py
import numpy as np
from skimage import measure


# ============================================================
# DUAL CONTOURING WRAPPER
# ============================================================

class DualContouring:
    """
    Currently backed by Marching Cubes.
    Structured so true DC can be swapped later.
    """

    def __init__(self, sdf_func, bounds=1.0, resolution=128):
        self.sdf_func = sdf_func
        self.bounds = bounds
        self.resolution = resolution

    def extract(self):

        xs = np.linspace(-self.bounds, self.bounds, self.resolution)
        grid = np.stack(
            np.meshgrid(xs, xs, xs, indexing="ij"), -1
        ).reshape(-1, 3)

        phi = self.sdf_func(grid).reshape(
            self.resolution,
            self.resolution,
            self.resolution
        )

        spacing = (2 * self.bounds) / (self.resolution - 1)
        origin = np.array([-self.bounds]*3)

        extractor = SurfaceExtractor()
        verts, faces, normals = extractor.extract(phi, spacing, origin)

        return verts, faces, normals


# ============================================================
# SURFACE EXTRACTION
# ============================================================

class SurfaceExtractor:

    def extract(self, phi, spacing, origin):

        verts, faces, normals, _ = measure.marching_cubes(
            phi,
            level=0.0,
            spacing=(spacing, spacing, spacing),
        )

        verts += origin

        return verts, faces, normals


# ============================================================
# QUAD BUILDER
# ============================================================

class QuadBuilder:

    @staticmethod
    def triangles_to_quads(faces):
        quads = []
        used = set()

        for i, f1 in enumerate(faces):
            if i in used:
                continue

            for j in range(i + 1, len(faces)):
                if j in used:
                    continue

                f2 = faces[j]
                shared = set(f1) & set(f2)

                if len(shared) == 2:
                    quad = list(set(f1) | set(f2))
                    if len(quad) == 4:
                        quads.append(quad)
                        used.add(i)
                        used.add(j)
                        break

        return quads


# ============================================================
# NORMAL COMPUTATION
# ============================================================

class NormalComputer:

    @staticmethod
    def compute_vertex_normals(verts, faces):

        normals = np.zeros_like(verts)

        for tri in faces:
            v0, v1, v2 = verts[tri]
            n = np.cross(v1 - v0, v2 - v0)
            n /= (np.linalg.norm(n) + 1e-8)

            normals[tri[0]] += n
            normals[tri[1]] += n
            normals[tri[2]] += n

        norms = np.linalg.norm(normals, axis=1) + 1e-8
        normals /= norms[:, None]

        return normals


# ============================================================
# UV MAPPING
# ============================================================

class UVMapper:

    @staticmethod
    def triplanar_uv(verts):

        uv = np.zeros((len(verts), 2))

        axis = np.argmax(np.abs(verts), axis=1)

        uv[axis == 0] = verts[axis == 0][:, 1:3]
        uv[axis == 1] = verts[axis == 1][:, [0, 2]]
        uv[axis == 2] = verts[axis == 2][:, 0:2]

        uv -= uv.min(0)
        uv /= uv.max(0) + 1e-8

        return uv


# ============================================================
# MESH CLEANUP
# ============================================================

class MeshCleaner:

    @staticmethod
    def remove_degenerate_faces(verts, faces):
        clean = []

        for tri in faces:
            v0, v1, v2 = verts[tri]
            area = np.linalg.norm(np.cross(v1 - v0, v2 - v0))
            if area > 1e-10:
                clean.append(tri)

        return np.array(clean)


# ============================================================
# EXPORTERS
# ============================================================

class OBJExporter:

    def export(self, verts, faces, normals=None, uv=None, path="mesh.obj"):

        with open(path, "w") as f:

            for v in verts:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")

            if uv is not None:
                for t in uv:
                    f.write(f"vt {t[0]} {t[1]}\n")

            if normals is not None:
                for n in normals:
                    f.write(f"vn {n[0]} {n[1]} {n[2]}\n")

            for tri in faces:
                if uv is not None and normals is not None:
                    f.write(
                        f"f {tri[0]+1}/{tri[0]+1}/{tri[0]+1} "
                        f"{tri[1]+1}/{tri[1]+1}/{tri[1]+1} "
                        f"{tri[2]+1}/{tri[2]+1}/{tri[2]+1}\n"
                    )
                else:
                    f.write(
                        f"f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n"
                    )

        return path


class SCADExporter:

    def export(self, verts, faces, path="mesh.scad"):

        with open(path, "w") as f:
            f.write("polyhedron(points=[\n")
            for v in verts:
                f.write(f"[{v[0]},{v[1]},{v[2]}],\n")

            f.write("], faces=[\n")
            for tri in faces:
                f.write(f"[{tri[0]},{tri[1]},{tri[2]}],\n")

            f.write("]);\n")

        return path
