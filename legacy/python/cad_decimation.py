# cad_decimation.py

import trimesh

class MeshDecimator:

    def simplify(self, mesh, ratio=0.5):
        tm = trimesh.Trimesh(
            vertices=mesh["verts"],
            faces=mesh["faces"]
        )

        target = int(len(tm.faces) * ratio)
        simplified = tm.simplify_quadratic_decimation(target)

        return {
            "verts": simplified.vertices,
            "faces": simplified.faces,
            "normals": simplified.vertex_normals
        }