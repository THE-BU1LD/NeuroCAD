# test_full_system_object.py

import os
from cad_master_kernel import CADKernel, SDFGraph

# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------

OUTPUT_DIR = "test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

kernel = CADKernel(resolution=320)
graph = SDFGraph()

# ------------------------------------------------------------
# 1️⃣ Base Block
# ------------------------------------------------------------

base = kernel._kernel._make_sdf(
    "box",
    {"size": [0.6, 0.4, 0.2]}
)

graph.add(base)

# ------------------------------------------------------------
# 2️⃣ Smooth Dome On Top
# ------------------------------------------------------------

dome = kernel._kernel._make_sdf(
    "sphere",
    {"radius": 0.35}
)

graph.smooth_add(dome, k=0.25)

# ------------------------------------------------------------
# 3️⃣ Central Vertical Drill
# ------------------------------------------------------------

central_drill = kernel._kernel.drill_z(radius=0.12)
graph.subtract(central_drill)

# ------------------------------------------------------------
# 4️⃣ Side Mount Holes (4 Cylinders)
# ------------------------------------------------------------

def offset_cylinder(x_offset, y_offset):
    prim = kernel._kernel.prim
    return lambda x: prim.cylinder(
        x - x.new_tensor([x_offset, y_offset, 0.0]),
        0.07,
        1.5
    )

mount_offsets = [
    (0.35, 0.2),
    (-0.35, 0.2),
    (0.35, -0.2),
    (-0.35, -0.2)
]

for ox, oy in mount_offsets:
    graph.subtract(offset_cylinder(ox, oy))

# ------------------------------------------------------------
# 5️⃣ Internal Rib
# ------------------------------------------------------------

rib = kernel._kernel._make_sdf(
    "box",
    {"size": [0.1, 0.5, 0.15]}
)

graph.add(rib)

# ------------------------------------------------------------
# 6️⃣ Build + Hollow
# ------------------------------------------------------------

print("Building mesh...")

mesh = kernel.build(
    graph=graph,
    hollow=0.05
)

print("Mesh generated:")
print("Vertices:", len(mesh["verts"]))
print("Faces:", len(mesh["faces"]))
# ------------------------------------------------------------
# 7️⃣ Export SCAD Only (Embedded Mesh)
# ------------------------------------------------------------

DOWNLOADS_DIR = os.path.expanduser("~/Downloads")
model_name = "neural_clay_mount"

scad_path = os.path.join(DOWNLOADS_DIR, f"{model_name}.scad")

def export_scad_polyhedron(mesh, path):
    with open(path, "w") as f:
        f.write("polyhedron(\n")
        f.write("points=[\n")

        for v in mesh["verts"]:
            f.write(f"[{v[0]}, {v[1]}, {v[2]}],\n")

        f.write("],\nfaces=[\n")

        for tri in mesh["faces"]:
            f.write(f"[{tri[0]}, {tri[1]}, {tri[2]}],\n")

        f.write("]\n);\n")

export_scad_polyhedron(mesh, scad_path)

print("Exported:")
print("SCAD:", scad_path)
print("Test complete.")
