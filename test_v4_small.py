from cad_master_kernel import CADKernel

print("Building optimized test...")

kernel = CADKernel(resolution=160, neural=True)
graph = kernel.new_graph()

graph.add(kernel.primitive("sphere", r=0.8))
graph.add(kernel.primitive("torus", R=0.6, r=0.2))
graph.smooth_add(kernel.primitive("cylinder", r=0.2, h=1.5), k=0.15)
graph.subtract(kernel.primitive("box", size=[0.3,0.3,0.3]))

mesh = kernel.build(graph, bounds=1.5, decimate=0.2)

info = kernel.analyze(mesh)
print("Mesh stats:", info)

kernel.export_stl(mesh, "v4_small.stl")
kernel.export_scad(mesh, "v4_small.scad")

print("Done.")