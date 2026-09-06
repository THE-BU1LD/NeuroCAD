import numpy as np
from cad_intelligence_core import SDF, MarchingCubes, STEPExporter, SCADExporter


class Round3Shape:

    def torus(self, p, R=1.3, r=0.45):
        x = p[..., 0]
        y = p[..., 1]
        z = p[..., 2]
        q = np.sqrt(x**2 + z**2) - R
        return np.sqrt(q**2 + y**2) - r

    def sphere(self, p, r=0.7):
        return np.linalg.norm(p, axis=-1) - r

    def ridges(self, p):
        x = p[..., 0]
        y = p[..., 1]
        z = p[..., 2]
        return 0.15 * np.sin(12 * x) * np.sin(12 * y) * np.sin(12 * z)

    def sdf(self, p):
        d1 = self.torus(p)
        d2 = self.sphere(p + np.array([0.6, 0.2, 0.0]))
        base = np.minimum(d1, d2)
        return base + self.ridges(p)


if __name__ == "__main__":

    print("\n[ROUND-3] Generating high-detail implicit CAD geometry")

    shape = Round3Shape()
    sdf = SDF()
    mc = MarchingCubes()
    step = STEPExporter()
    scad = SCADExporter()

    # ---- grid sampling ----
    bounds = 2.2
    res = 110
    grid, spacing = sdf.grid(shape.sdf, bounds=bounds, res=res)

    # IMPORTANT: origin must match SDF grid domain
    origin = np.array([-bounds, -bounds, -bounds])

    # ---- extract with refinement + normals ----
    verts, faces, normals = mc.extract(
        grid,
        spacing=spacing,
        origin=origin,
        refine=True,
        return_normals=True
    )

    print("Vertices:", len(verts))
    print("Faces:", len(faces))

    # ---- export ----
    step_file = step.export(verts, faces, "round3_output.step")
    scad_file = scad.export(verts, faces, "round3_output.scad")

    print("STEP:", step_file)
    print("SCAD:", scad_file)