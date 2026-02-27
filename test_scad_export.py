from cad_kernel_master import CADKernel

k = CADKernel(resolution=128, use_octree=True)

mesh = k.build("frisbee")

k.export_scad(mesh, "frisbee.scad")

print("SCAD written: frisbee.scad")
