import torch
import numpy as np

from cad_sampling import OctreeSampler
from cad_meshing import DualContouring
from cad_quad_topology import QuadTopology
from cad_neural_sdf import NeuralShapeLibrary


# ==========================================================
# INSANE NEURAL SDF
# ==========================================================

def insane_sdf(p):
    if not torch.is_tensor(p):
        p = torch.tensor(p, dtype=torch.float32)

    g = NeuralShapeLibrary.gyroid(p, scale=10.0)
    n = NeuralShapeLibrary.fractal_noise(p)

    return g + 0.3 * n


# ==========================================================
# RUN TEST
# ==========================================================

def run_insane_test():

    print("\n=== INSANE CAD TEST ===")

    sampler = OctreeSampler(
        insane_sdf,
        bounds=1.2,
        depth=8,        # 🔥 deep octree
        device="cpu"
    )

    print("Sampling...")
    phi, spacing, origin = sampler.sample(256)

    print("Meshing...")
    dc = DualContouring()
    verts, faces, quads = dc.extract(phi, spacing, origin)

    print("Base verts:", len(verts))
    print("Base faces:", len(faces))

    edges = QuadTopology.count_edges(faces)
    print("Base edges:", edges)

    # ------------------------------------------------------
    # Subdivide twice for insane topology density
    # ------------------------------------------------------

    for i in range(2):
        print(f"Subdividing pass {i+1}...")
        verts, faces = QuadTopology.subdivide(verts, faces)

        edges = QuadTopology.count_edges(faces)

        print(f"After subdiv {i+1}:")
        print("  verts:", len(verts))
        print("  faces:", len(faces))
        print("  edges:", edges)

    print("\n=== FINAL OUTPUT ===")
    print("Verts:", len(verts))
    print("Faces:", len(faces))
    print("Edges:", edges)

    # ------------------------------------------------------
    # EXPORT SCAD
    # ------------------------------------------------------

    print("\nExporting SCAD...")

    exporter = SCADExporter()
    exporter.export(
        verts,
        faces,
        "insane_mesh.scad"
    )

    print("SCAD exported as insane_mesh.scad")


# ==========================================================

if __name__ == "__main__":
    run_insane_test()
