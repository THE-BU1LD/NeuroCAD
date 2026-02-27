import os
import numpy as np
from cad_master_kernel import CADKernelV2, SDFGraph

OUTPUT_DIR = os.path.expanduser("~/Downloads")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------------------------------
# KERNEL INIT
# -------------------------------------------------

kernel = CADKernelV2(
    resolution=300,   # increase to 350+ for even more faces
    neural=True
)

print("Using device:", kernel.device)

graph = SDFGraph()

# -------------------------------------------------
# MEGA PROCEDURAL FIELD
# -------------------------------------------------

def mega_field(p):
    # p is (N, 3) numpy array

    x = p[:, 0] * 8.0
    y = p[:, 1] * 8.0
    z = p[:, 2] * 8.0

    gyroid = (
        np.sin(x) * np.cos(y) +
        np.sin(y) * np.cos(z) +
        np.sin(z) * np.cos(x)
    )

    r = np.sqrt((p ** 2).sum(axis=1))
    shell = np.abs(r - 0.9) - 0.05

    return np.minimum(shell, np.abs(gyroid) - 0.2)

graph.add(mega_field)

# -------------------------------------------------
# BUILD (NO method ARGUMENT)
# -------------------------------------------------

print("Building mega object...")

mesh = kernel.build(
    graph=graph,
    decimate=0.0  # full resolution
)

print("Verts:", len(mesh["verts"]))
print("Faces:", len(mesh["faces"]))

# -------------------------------------------------
# EXPORT STL
# -------------------------------------------------

stl_path = os.path.join(OUTPUT_DIR, "mega_1M_object.stl")
kernel.export_stl(mesh, stl_path)

# -------------------------------------------------
# EXPORT SCAD WRAPPER
# -------------------------------------------------

scad_path = os.path.join(OUTPUT_DIR, "mega_1M_object.scad")

with open(scad_path, "w") as f:
    f.write(f'import("{stl_path}", convexity=20);\n')

print("Saved STL:", stl_path)
print("Saved SCAD:", scad_path)
print("Done.")