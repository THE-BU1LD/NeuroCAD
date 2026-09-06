from cad_master_kernel import CADKernel
import shutil
import subprocess
import math

print("Building a complex CAD test...")

kernel = CADKernel(resolution=200, neural=True)
graph = kernel.new_graph()

graph.add(kernel.primitive("sphere", r=1.0))
graph.add(kernel.primitive("torus", R=1.2, r=0.15))

for angle in range(0, 360, 45):
    rad = math.radians(angle)
    x = 0.8 * math.cos(rad)
    y = 0.8 * math.sin(rad)
    graph.smooth_add(kernel.primitive("cylinder", r=0.1, h=2.0), k=0.1)


for i in range(-1, 2):
    for j in range(-1, 2):
        graph.subtract(kernel.primitive("box", size=[0.2, 0.2, 0.5]))

for i in range(-2, 3):
    for j in range(-2, 3):
        graph.smooth_add(kernel.primitive("sphere", r=0.05), k=0.05)

for i in range(4):
    graph.add(kernel.primitive("torus", R=0.4 + i*0.1, r=0.03))

mesh = kernel.build(graph, bounds=2.0, decimate=0.3)


info = kernel.analyze(mesh)
print("Complex Mesh stats:", info)

# ============================================================
# Export files
# ============================================================
kernel.export_stl(mesh, "v4_complex.stl")
scad_path = "v4_complex.scad"
kernel.export_scad(mesh, scad_path)
print(f"SCAD file exported: {scad_path}")

# Optional: auto-render to STL via OpenSCAD
output_stl = "v4_complex_from_scad.stl"
if shutil.which("openscad"):
    subprocess.run(["openscad", "-o", output_stl, scad_path])
    print(f"Rendered STL from SCAD: {output_stl}")
else:
    print("OpenSCAD not installed, skipping render.")

print("Done.")