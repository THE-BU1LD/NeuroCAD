import os
import math
import cad_master_kernel

# -------------------------------------------------
# SETUP
# -------------------------------------------------

OUTPUT_DIR = os.path.expanduser("~/Downloads")
os.makedirs(OUTPUT_DIR, exist_ok=True)

kernel = cad_master_kernel.CADKernelV2(
    resolution=160,      # DC works better slightly lower
    octree_depth=6,
    neural=True
)

graph = cad_master_kernel.SDFGraph()

# -------------------------------------------------
# PRIMITIVES
# -------------------------------------------------

prim = kernel.prim

def sphere(r):
    return lambda x: prim.sphere(x, r)

def box(size):
    return lambda x: prim.box(x, size)

def cylinder(r, h):
    return lambda x: prim.cylinder(x, r, h)

def torus(R, r):
    return lambda x: prim.torus(x, R, r)

# -------------------------------------------------
# BASE PLATFORM
# -------------------------------------------------

graph.add(box([0.8, 0.6, 0.15]))

# -------------------------------------------------
# MAIN BODY (SMOOTH BLEND)
# -------------------------------------------------

graph.smooth_add(sphere(0.5), k=0.3)

# -------------------------------------------------
# TOP TORUS CUT
# -------------------------------------------------

graph.subtract(torus(0.45, 0.08))

# -------------------------------------------------
# RADIAL HOLES (6)
# -------------------------------------------------

def radial_hole(angle_deg):
    a = math.radians(angle_deg)
    x = 0.5 * math.cos(a)
    y = 0.5 * math.sin(a)

    return lambda p: prim.cylinder(
        p - p.new_tensor([x, y, 0.0]),
        0.07,
        2.0
    )

for angle in range(0, 360, 60):
    graph.subtract(radial_hole(angle))

# -------------------------------------------------
# INTERNAL RIBS
# -------------------------------------------------

graph.add(box([0.1, 0.7, 0.2]))
graph.add(box([0.7, 0.1, 0.2]))

# -------------------------------------------------
# BUILD (Dual Contouring)
# -------------------------------------------------

print("Building complex object using Dual Contouring...")

mesh = kernel.build(
    graph=graph,
    decimate=0.6  # optional mesh reduction
)

print("Vertices:", len(mesh["verts"]))
print("Faces:", len(mesh["faces"]))

# -------------------------------------------------
# EXPORT SCAD POLYHEDRON
# -------------------------------------------------

model_name = "hyper_complex_clay_object_v2"
scad_path = os.path.join(OUTPUT_DIR, f"{model_name}.scad")

def export_scad_poly(mesh, path):
    with open(path, "w") as f:
        f.write("polyhedron(\npoints=[\n")
        for v in mesh["verts"]:
            f.write(f"[{v[0]}, {v[1]}, {v[2]}],\n")
        f.write("],\nfaces=[\n")
        for tri in mesh["faces"]:
            f.write(f"[{tri[0]}, {tri[1]}, {tri[2]}],\n")
        f.write("]\n);\n")

export_scad_poly(mesh, scad_path)

print("Saved to:", scad_path)
print("Done.")