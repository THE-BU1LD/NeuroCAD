import trimesh
from neural_sdf import NeuralTrainer
from cuda_mc import CUDAMarchingCubes
from topology_opt import DifferentiableTopology
from nurbs_fit import ImplicitToNURBS


class CADEngineV6:

    def __init__(self):
        self.trainer = NeuralTrainer()
        self.mc = CUDAMarchingCubes()
        self.nurbs = ImplicitToNURBS()

    def build_from_mesh(self, verts):

        model = self.trainer.train_surface(verts)

        topo = DifferentiableTopology(model)
        scale = topo.optimize_volume(0.2)

        verts, faces = self.mc.extract(model, res=140)

        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        volume = mesh.volume
        area = mesh.area

        spline = self.nurbs.fit_patch(verts)

        return {
            "verts": len(verts),
            "faces": len(faces),
            "volume": volume,
            "area": area,
            "scale": scale,
            "nurbs_patch": spline
        }
