import os
from cad_master_kernel import CADKernel
from cad_text_bridge import TextToGraph

OUTPUT_DIR = os.path.expanduser("~/Downloads")
os.makedirs(OUTPUT_DIR, exist_ok=True)

kernel = CADKernel(resolution=140, neural=True)

text_system = TextToGraph(kernel)

graph = text_system.parse(
    "base platform with dome and torus cut and cylinder holes"
)

print("Building hyper object...")

mesh = kernel.build(graph, decimate=0.4)

print("Verts:", len(mesh["verts"]))
print("Faces:", len(mesh["faces"]))

# -------------------------------------------------
# EXPORT
# -------------------------------------------------

model_name = "hyper_v4_object"

stl_path = os.path.join(OUTPUT_DIR, f"{model_name}.stl")
scad_path = os.path.join(OUTPUT_DIR, f"{model_name}.scad")

# Export STL
kernel.export_stl(mesh, stl_path)

# Export SCAD wrapper
with open(scad_path, "w") as f:
    f.write(f'import("{stl_path}");\n')

print("Saved STL :", stl_path)
print("Saved SCAD:", scad_path)
print("Done.")