from cad_master_kernel import CADKernel
import torch

kernel = CADKernel()

kernel.auto_resolution(1_000_000)

graph = kernel.new_graph()

sphere = kernel.primitive("sphere",r=1.0)
box = kernel.primitive("box",size=[0.6,0.6,0.6])
torus = kernel.primitive("torus",R=0.9,r=0.25)

graph.add(sphere)
graph.smooth_add(torus,0.2)
graph.subtract(box)

mesh = kernel.build(graph)

stats = kernel.analyze(mesh)

print("\nMesh Stats")
print(stats)

kernel.export_stl(mesh,"neurocad_demo.stl")
kernel.export_scad(mesh,"neurocad_demo.scad")

print("\nSaved neurocad_demo.stl")
print("Saved neurocad_demo.scad")