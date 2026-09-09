import os
import time
import numpy as np
import torch
import cad_master_kernel as cmk

print("\n=== NeuroCAD SMT Ultra (KLEIN BOTTLE TEST) ===\n")

OUTPUT_DIR = "output_models"
RES = 96
BOUNDS = 2.5
os.makedirs(OUTPUT_DIR, exist_ok=True)
np.random.seed(42)

# ----------------------------
# Klein Bottle SDF
# ----------------------------
class KleinSDF:
    def __call__(self, pts):
        x = pts[:, 0]
        y = pts[:, 1]
        z = pts[:, 2]

        a = 2.0
        r = (x**2 + y**2 + z**2 + a**2 - 2*a*y)
        f = r**2 - 8*a**2*(x**2 + z**2)

        return f

# ----------------------------
# Build Graph
# ----------------------------
def build_graph():
    return KleinSDF()

# ----------------------------
# SDF Evaluator
# ----------------------------
def eval_sdf(sdf, pts):
    pts_np = np.array(pts, dtype=np.float32)

    # ✅ Custom SDF
    if callable(sdf):
        return sdf(pts_np).astype(np.float32).flatten()

    # ✅ Kernel FieldSampler
    try:
        sampler = cmk.FieldSampler(sdf)
        if hasattr(sampler, "sample"):
            result = sampler.sample(torch.tensor(pts_np))
        else:
            result = sampler.evaluate(torch.tensor(pts_np))
        return result.detach().cpu().numpy().flatten()
    except Exception:
        result = None

    # ✅ Kernel Batched evaluator
    try:
        sampler = cmk.BatchedSDFEvaluator(sdf, device='cpu')
        result = sampler.evaluate(torch.tensor(pts_np))
        return result.detach().cpu().numpy().flatten()
    except Exception:
        result = None

    # Fallback
    return np.linalg.norm(pts_np, axis=1) - 1.0

# ----------------------------
# Mesh Builder
# ----------------------------
def build_mesh(sdf):
    print("\nExtracting mesh...\n")
    start = time.time()

    lin = np.linspace(-BOUNDS, BOUNDS, RES)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

    print("Sampling SDF (kernel-aligned)...")
    values = eval_sdf(sdf, pts)
    field = values.reshape((RES, RES, RES))

    print("Running marching cubes...")

    mc = cmk.MarchingCubes()
    verts, faces, _ = mc.extract(field, BOUNDS)

    if verts is None or faces is None or len(verts) == 0:
        raise Exception("Empty mesh")

    verts = np.asarray(verts, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.int32)

    print(f"Vertices: {verts.shape}, Faces: {faces.shape}")
    print("Time:", round(time.time() - start, 2), "s")

    return {
        "verts": verts,
        "faces": faces
    }

# ----------------------------
# STL Export
# ----------------------------
def export(mesh_data):
    path = os.path.join(OUTPUT_DIR, "klein_bottle.stl")

    try:
        exporter = cmk.MeshExporter()
        exporter.export_stl(mesh_data, path)
        print("Saved STL:", path)
    except Exception as e:
        print("Export failed:", e)

# ----------------------------
# SCAD Export
# ----------------------------
def export_scad():
    path = os.path.join(OUTPUT_DIR, "klein_bottle.scad")

    scad_code = f"""
// === Klein Bottle (Parametric Approximation) ===
$fn = {RES};

module klein() {{
    for (u = [0:10:360]) {{
        for (v = [0:10:360]) {{

            x = (2 + cos(v)) * cos(u);
            y = (2 + cos(v)) * sin(u);
            z = sin(v);

            translate([x, y, z])
                sphere(r = 0.08);
        }}
    }}
}}

scale([0.4,0.4,0.4])
    klein();
"""

    with open(path, "w") as f:
        f.write(scad_code)

    print("Saved SCAD:", path)

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    sdf = build_graph()
    mesh_data = build_mesh(sdf)

    export(mesh_data)      # STL (kernel)
    export_scad()          # SCAD fallback

    print("\n=== DONE ===\n")
