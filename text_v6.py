import trimesh
from engine_v6 import CADEngineV6

if __name__ == "__main__":

    mesh = trimesh.creation.torus()
    verts = mesh.vertices

    engine = CADEngineV6()
    result = engine.build_from_mesh(verts)

    print(result)
