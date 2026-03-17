import os
import time
import numpy as np

import cad_master_kernel

# ------------------------------------------------
# Auto-detect Kernel + Batch
# ------------------------------------------------

if hasattr(cad_master_kernel, "CADKernel"):
    KernelClass = cad_master_kernel.CADKernel
elif hasattr(cad_master_kernel, "Kernel"):
    KernelClass = cad_master_kernel.Kernel
else:
    raise Exception("No Kernel class found in cad_master_kernel")

if hasattr(cad_master_kernel, "GPUBatch"):
    GPUBatch = cad_master_kernel.GPUBatch
else:
    raise Exception("No GPUBatch found")

print("\n=== NeuroCAD SMT Ultra Test (FINAL AUTO) ===\n")

# ------------------------------------------------
# Config
# ------------------------------------------------

OUTPUT_DIR = "output_models"
RESOLUTION = 320
TARGET_SAMPLES = 6_000_000
MESH_BOUNDS = 1.8
CHUNK_SIZE = 500_000
BATCH_COUNT = 3

os.makedirs(OUTPUT_DIR, exist_ok=True)
np.random.seed(42)

# ------------------------------------------------
# Noise System
# ------------------------------------------------

class SDFNoise:

    @staticmethod
    def noise(p):
        return (
            np.sin(2.3*p[0]) *
            np.cos(2.1*p[1]) *
            np.sin(2.7*p[2])
        )

    @staticmethod
    def fractal(p, octaves=3):
        val, amp, freq = 0.0, 1.0, 1.0
        for _ in range(octaves):
            val += amp * SDFNoise.noise(p * freq)
            freq *= 2.0
            amp *= 0.5
        return val

    @staticmethod
    def perturb(primitive, strength=0.05):
        original_sdf = primitive.sdf

        def new_sdf(p):
            return original_sdf(p + strength * SDFNoise.fractal(p))

        primitive.sdf = new_sdf
        return primitive


# ------------------------------------------------
# Kernel Init
# ------------------------------------------------

kernel = KernelClass(resolution=RESOLUTION)

if hasattr(kernel, "auto_resolution"):
    kernel.auto_resolution(TARGET_SAMPLES)

print("Kernel initialized")

# ------------------------------------------------
# Graph creator (auto)
# ------------------------------------------------

def new_graph(kernel):
    if hasattr(kernel, "new_graph"):
        return kernel.new_graph()
    elif hasattr(kernel, "graph"):
        return kernel.graph()
    else:
        raise Exception("No graph creation method found")

# ------------------------------------------------
# Jacobian Warp
# ------------------------------------------------

def jacobian_warp_sdf(sdf):

    def warped(p):

        eps = 1e-3

        def field(x):
            return SDFNoise.fractal(x * 2.0)

        grad = np.array([
            field(p + [eps,0,0]) - field(p - [eps,0,0]),
            field(p + [0,eps,0]) - field(p - [0,eps,0]),
            field(p + [0,0,eps]) - field(p - [0,0,eps]),
        ]) / (2 * eps)

        J = np.outer(grad, grad)
        warped_p = p + 0.12 * (J @ p)

        return sdf(warped_p)

    return warped


# ------------------------------------------------
# Clone helper
# ------------------------------------------------

def clone_primitive(kernel, p):
    if hasattr(p, "type") and hasattr(p, "params"):
        return kernel.primitive(p.type, **p.params)
    return p


# ------------------------------------------------
# Build Graph
# ------------------------------------------------

graph = new_graph(kernel)

shell = kernel.primitive("sphere", r=1.0)
core = kernel.primitive("sphere", r=0.82)

graph.add(shell)
graph.subtract(core)

# Rings
for r, t in [(0.7, 0.14), (0.5, 0.1), (0.3, 0.08)]:
    graph.add(kernel.primitive("torus", R=r, r=t))

# Cuts
for angle in np.linspace(0, 2*np.pi, 6, endpoint=False):
    x = 0.5 * np.cos(angle)
    y = 0.5 * np.sin(angle)

    cut = kernel.primitive("cylinder", r=0.12, h=2.5)
    if hasattr(cut, "translate"):
        cut.translate([x, y, 0])

    graph.subtract(cut)

# ------------------------------------------------
# Multi-field deformation
# ------------------------------------------------

base = kernel.primitive("sphere", r=0.95)

low = SDFNoise.perturb(clone_primitive(kernel, base), 0.03)
mid = SDFNoise.perturb(clone_primitive(kernel, base), 0.05)
high = SDFNoise.perturb(clone_primitive(kernel, base), 0.02)

if hasattr(graph, "smooth_add"):
    graph.smooth_add(low, k=0.2)
    graph.smooth_add(mid, k=0.12)
    graph.smooth_add(high, k=0.08)
else:
    graph.add(low)
    graph.add(mid)
    graph.add(high)

# ------------------------------------------------
# Inject Warp
# ------------------------------------------------

if hasattr(graph, "sdf"):
    original_sdf = graph.sdf
    graph.sdf = jacobian_warp_sdf(original_sdf)

# ------------------------------------------------
# Build Mesh
# ------------------------------------------------

print("\nBuilding mesh...\n")

start = time.time()

mesh = kernel.build(
    graph,
    bounds=MESH_BOUNDS,
    chunk=CHUNK_SIZE
)

print("Build time:", round(time.time() - start, 2), "s")
print("Vertices:", len(mesh["verts"]))
print("Faces:", len(mesh["faces"]))

# ------------------------------------------------
# Analysis
# ------------------------------------------------

if hasattr(kernel, "analyze"):
    analysis = kernel.analyze(mesh)
else:
    analysis = {}

def curvature_proxy(verts):
    v = np.array(verts)
    c = np.mean(v, axis=0)
    return np.var(np.linalg.norm(v - c, axis=1))

analysis["curvature_proxy"] = curvature_proxy(mesh["verts"])

print("\n--- Analysis ---")
for k, v in analysis.items():
    print(f"{k}: {v}")

# ------------------------------------------------
# Export
# ------------------------------------------------

stl_path = os.path.join(OUTPUT_DIR, "smt_ultra_model.stl")

if hasattr(kernel, "export_stl"):
    kernel.export_stl(mesh, stl_path)
    print("\nSaved:", stl_path)
else:
    print("\nNo STL export method found")

# ------------------------------------------------
# Batch
# ------------------------------------------------

batch = GPUBatch(kernel)

def safe_add(batch, job, path):
    if hasattr(batch, "add_job"):
        batch.add_job(job, path)
    elif hasattr(batch, "submit"):
        batch.submit(job, path)
    elif hasattr(batch, "add"):
        batch.add(job, path)

def safe_run(batch):
    if hasattr(batch, "run_all"):
        batch.run_all()
    elif hasattr(batch, "run"):
        batch.run()
    elif hasattr(batch, "execute"):
        batch.execute()

def parametric_graph(k, seed):

    np.random.seed(seed)
    g = new_graph(k)

    g.add(k.primitive("sphere", r=0.6 + 0.1*np.random.rand()))

    for _ in range(3):
        g.add(k.primitive(
            "torus",
            R=0.3 + 0.3*np.random.rand(),
            r=0.05 + 0.1*np.random.rand()
        ))

    return g

print("\nRunning batch...\n")

for i in range(BATCH_COUNT):

    def job(k, s=i):
        return parametric_graph(k, s)

    path = os.path.join(OUTPUT_DIR, f"smt_batch_{i}.stl")
    safe_add(batch, job, path)

safe_run(batch)

print("\n=== DONE ===\n")