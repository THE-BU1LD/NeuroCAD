from cad_kernel_master import CADKernel
from text_to_cad import TextToCAD

kernel = CADKernel(resolution=128, use_octree=True)
t2c = TextToCAD(kernel)

mesh = t2c.build("a cylinder radius 0.3 height 1.2")

kernel.export_scad(mesh, "text_cylinder.scad")

print("Generated from text → text_cylinder.scad")
