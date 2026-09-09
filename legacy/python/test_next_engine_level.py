import os

import torch
from cad_master_kernel import CADKernel

OUTPUT = os.path.expanduser("~/Downloads")

kernel = CADKernel(resolution=192, neural=True)
kernel.auto_resolution(1_000_000)

graph = kernel.new_graph()

graph.add(kernel.primitive("box", size=[0.8,0.6,0.2]))
graph.smooth_add(kernel.primitive("sphere", r=0.7), k=0.3)
graph.subtract(kernel.primitive("torus", R=0.6, r=0.1))

for a in range(0,360,30):
    import math
    x = 0.6*math.cos(math.radians(a))
    y = 0.6*math.sin(math.radians(a))
    graph.subtract(
        lambda p, x=x, y=y:
        kernel.prim.cylinder(
            p - torch.tensor([x,y,0], device=p.device),
            0.08, 2.0
        )
    )

print("Building adaptive mega object...")

mesh = kernel.build(graph, decimate=0.1)

analysis = kernel.analyze(mesh)
print(analysis)

stl_path = os.path.join(OUTPUT, "next_level_engine.stl")
scad_path = os.path.join(OUTPUT, "next_level_engine.scad")

kernel.export_stl(mesh, stl_path)
kernel.export_scad(mesh, scad_path)

print("Saved:", stl_path)
print("Saved:", scad_path)