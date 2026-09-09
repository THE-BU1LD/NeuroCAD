import os
from cad_master_kernel import CADKernel
from cad_text_bridge import TextToGraph

OUTPUT_DIR = os.path.expanduser("~/Downloads")

kernel = CADKernel(
    resolution=220,     # High density
    neural=True
)

bridge = TextToGraph(kernel)

graph = bridge.parse(
    "platform with dome and torus and holes"
)

print("Building mega object...")

mesh = kernel.build(
    graph,
    bounds=1.5,
    decimate=0.0
)

print("Verts:", len(mesh["verts"]))
print("Faces:", len(mesh["faces"]))

stl_path = os.path.join(OUTPUT_DIR, "hyper_v5_object.stl")
scad_path = os.path.join(OUTPUT_DIR, "hyper_v5_object.scad")

kernel.export_stl(mesh, stl_path)
kernel.export_scad(mesh, scad_path)

print("Saved STL:", stl_path)
print("Saved SCAD:", scad_path)
print("Done.")