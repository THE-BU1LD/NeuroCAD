from cad_master_kernel import CADKernel
import os

print("Building 1M+ face object...")

kernel = CADKernel(resolution=256, neural=True)
graph = kernel.new_graph()

# Complex high-detail geometry
graph.add(kernel.primitive("sphere", r=0.8))
graph.add(kernel.primitive("torus", R=0.6, r=0.2))
graph.subtract(kernel.primitive("box", size=[0.3,0.3,0.3]))
graph.smooth_add(kernel.primitive("cylinder", r=0.25, h=1.2), k=0.15)

mesh = kernel.build(
    graph,
    bounds=1.5,
    decimate=0.0
)

print("Verts:", len(mesh["verts"]))
print("Faces:", len(mesh["faces"]))

# ---- Export Files ----

stl_path = "mega_1m_model.stl"
scad_path = "mega_1m_model.scad"

kernel.export_stl(mesh, stl_path)
kernel.export_scad(mesh, scad_path)

print("Saved STL:", stl_path)
print("Saved SCAD:", scad_path)

# ---- Auto Render SCAD ----

rendered_path = kernel.render_scad(scad_path)

print("Rendered from SCAD:", rendered_path)
print("Done.")