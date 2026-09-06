import numpy as np
from cad_intelligence_core import SDF, MarchingCubes, STEPExporter


class ComplexShape:
    def __init__(self):
        self.sdf = SDF()

    def torus(self, p, R=1.2, r=0.4):
        q = np.array([np.linalg.norm(p[[0,2]]) - R, p[1]])
        return np.linalg.norm(q) - r

    def sphere(self, p, r=0.6):
        return np.linalg.norm(p) - r

    def smooth_union(self, d1, d2, k=0.3):
        h = np.clip(0.5 + 0.5*(d2-d1)/k, 0, 1)
        return np.where(
            True,
            (d2*(1-h) + d1*h) - k*h*(1-h),
            None
        )

    def sdf_func(self, p):
        d1 = self.torus(p)
        d2 = self.sphere(p + np.array([0.5,0.3,0]))
        return self.smooth_union(d1, d2)


if __name__ == "__main__":

    shape = ComplexShape()
    sdf = SDF()
    mc = MarchingCubes()
    exporter = STEPExporter()

    grid, _ = sdf.grid(lambda p: shape.sdf_func(p), bounds=2.0, res=70)

    verts, faces = mc.extract(grid)

    file = exporter.export(verts, faces, filename="complex_test_output.scad")

    print("Vertices:", len(verts))
    print("Faces:", len(faces))
    print("Exported:", file)
