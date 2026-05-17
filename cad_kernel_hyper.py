from __future__ import annotations

from cad_master_kernel import CADKernelV2


class CADKernelHyper(CADKernelV2):
    def amplify(self, mesh, levels: int = 2):
        # Deterministic refinement: subdivide faces by repeated midpoint splitting.
        import numpy as np
        import trimesh

        verts = np.asarray(mesh["verts"], dtype=float)
        faces = np.asarray(mesh["faces"], dtype=int)
        tm = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        for _ in range(max(0, int(levels))):
            tm = tm.subdivide()
        return {"verts": tm.vertices.tolist(), "faces": tm.faces.tolist(), "mesh": tm}
