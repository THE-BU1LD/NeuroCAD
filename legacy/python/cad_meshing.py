# cad_meshing.py

import numpy as np
from skimage import measure


# ============================================================
# DUAL CONTOURING WRAPPER (MC BACKEND)
# ============================================================

class DualContouring:
    """
    Currently backed by Marching Cubes.
    Memory-efficient sampling.
    """

    def __init__(self, sdf_func, bounds=1.0, resolution=128):
        self.sdf_func = sdf_func
        self.bounds = bounds
        self.resolution = resolution

    def extract(self):

        xs = np.linspace(-self.bounds, self.bounds, self.resolution)
        spacing = (2 * self.bounds) / (self.resolution - 1)
        origin = np.array([-self.bounds] * 3)

        phi = np.zeros(
            (self.resolution, self.resolution, self.resolution),
            dtype=np.float32
        )

        # Memory-efficient slice sampling
        for i, x in enumerate(xs):
            yz = np.stack(np.meshgrid(xs, xs, indexing="ij"), -1)

            pts = np.column_stack([
                np.full(yz.shape[0] * yz.shape[1], x),
                yz[..., 0].ravel(),
                yz[..., 1].ravel()
            ])

            phi[i] = self.sdf_func(pts).reshape(
                self.resolution, self.resolution
            )

        extractor = SurfaceExtractor()
        verts, faces = extractor.extract(phi, spacing, origin)

        return verts, faces


# ============================================================
# SURFACE EXTRACTION
# ============================================================

class SurfaceExtractor:

    def extract(self, phi, spacing, origin):

        verts, faces, _, _ = measure.marching_cubes(
            phi,
            level=0.0,
            spacing=(spacing, spacing, spacing),
        )

        verts += origin
        return verts, faces


# ============================================================
# QUAD BUILDER (O(N))
# ============================================================

class QuadBuilder:

    @staticmethod
    def triangles_to_quads(faces):

        edge_map = {}
        quads = []

        for i, tri in enumerate(faces):

            edges = [
                tuple(sorted((tri[0], tri[1]))),
                tuple(sorted((tri[1], tri[2]))),
                tuple(sorted((tri[2], tri[0])))
            ]

            for e in edges:
                if e in edge_map:
                    j = edge_map[e]
                    other = faces[j]

                    quad = list(set(tri) | set(other))
                    if len(quad) == 4:
                        quads.append(quad)
                else:
                    edge_map[e] = i

        return quads


# ============================================================
# NORMAL COMPUTATION (VECTORIZED)
# ============================================================

class NormalComputer:

    @staticmethod
    def compute_vertex_normals(verts, faces):

        v0 = verts[faces[:, 0]]
        v1 = verts[faces[:, 1]]
        v2 = verts[faces[:, 2]]

        face_normals = np.cross(v1 - v0, v2 - v0)
        face_normals /= (
            np.linalg.norm(face_normals, axis=1, keepdims=True) + 1e-8
        )

        normals = np.zeros_like(verts)

        np.add.at(normals, faces[:, 0], face_normals)
        np.add.at(normals, faces[:, 1], face_normals)
        np.add.at(normals, faces[:, 2], face_normals)

        normals /= (
            np.linalg.norm(normals, axis=1, keepdims=True) + 1e-8
        )

        return normals


# ============================================================
# UV MAPPING (TRIPLANAR BLEND)
# ============================================================

class UVMapper:

    @staticmethod
    def triplanar_uv(verts, normals):

        weights = np.abs(normals)
        weights /= weights.sum(axis=1, keepdims=True) + 1e-8

        uv_x = verts[:, 1:3]
        uv_y = verts[:, [0, 2]]
        uv_z = verts[:, 0:2]

        uv = (
            weights[:, [0]] * uv_x +
            weights[:, [1]] * uv_y +
            weights[:, [2]] * uv_z
        )

        uv -= uv.min(0)
        uv /= uv.max(0) + 1e-8

        return uv


# ============================================================
# MESH CLEANUP
# ============================================================

class MeshCleaner:

    @staticmethod
    def remove_degenerate_faces(verts, faces):
        v0 = verts[faces[:, 0]]
        v1 = verts[faces[:, 1]]
        v2 = verts[faces[:, 2]]

        area = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
        mask = area > 1e-10

        return faces[mask]

    @staticmethod
    def deduplicate(verts, faces, tol=1e-6):

        rounded = np.round(verts / tol).astype(np.int64)

        _, unique_idx, inverse = np.unique(
            rounded,
            axis=0,
            return_index=True,
            return_inverse=True
        )

        verts = verts[unique_idx]
        faces = inverse[faces]

        return verts, faces


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