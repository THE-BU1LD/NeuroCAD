"""
test_frisbee_100k_scad.py

High-resolution frisbee (~100k+ faces)
Exports as OpenSCAD polyhedron.
"""

import numpy as np
import time
from skimage import measure


# ============================================================
# FRISBEE SDF
# ============================================================

def sdf_frisbee(p):

    outer_radius = 1.0
    thickness = 0.08
    hole_radius = 0.35
    rim_radius = 0.15

    x, y, z = p[...,0], p[...,1], p[...,2]
    r = np.sqrt(x*x + y*y)

    disk = np.maximum(r - outer_radius, np.abs(z) - thickness)
    hole = hole_radius - r
    torus = np.sqrt((r - (outer_radius - rim_radius))**2 + z*z) - rim_radius

    base = np.minimum(disk, torus)
    frisbee = np.maximum(base, hole)

    return frisbee


# ============================================================
# GRID SAMPLER
# ============================================================

def sample_grid(resolution, bounds=1.5):

    lin = np.linspace(-bounds, bounds, resolution)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")
    pts = np.stack([X, Y, Z], axis=-1)

    phi = sdf_frisbee(pts)

    spacing = (2*bounds) / resolution
    origin = np.array([-bounds, -bounds, -bounds])

    return phi, spacing, origin


# ============================================================
# MESH EXTRACTION
# ============================================================

def generate_mesh(resolution):

    phi, spacing, origin = sample_grid(resolution)

    verts, faces, normals, _ = measure.marching_cubes(
        phi,
        level=0.0,
        spacing=(spacing, spacing, spacing)
    )

    verts += origin

    return verts, faces


# ============================================================
# FAST SCAD EXPORT
# ============================================================

def export_scad(path, verts, faces):

    with open(path, "w") as f:

        f.write("polyhedron(\n")
        f.write("  points=[\n")

        for v in verts:
            f.write(f"    [{v[0]},{v[1]},{v[2]}],\n")

        f.write("  ],\n")
        f.write("  faces=[\n")

        for tri in faces:
            f.write(f"    [{tri[0]},{tri[1]},{tri[2]}],\n")

        f.write("  ]\n")
        f.write(");\n")

    return path


# ============================================================
# TARGET FACE GENERATION
# ============================================================

def generate_target_faces(target_faces=100000):

    print("\n🔥 Generating High-Resolution Frisbee")
    print("Target faces:", target_faces)

    resolution = 128

    while True:

        print(f"\nTesting resolution: {resolution}")

        t0 = time.time()
        verts, faces = generate_mesh(resolution)
        t1 = time.time()

        face_count = len(faces)

        print("Faces:", face_count)
        print("Vertices:", len(verts))
        print("Time:", round(t1 - t0, 3), "seconds")

        if face_count >= target_faces:
            print("\n✅ Target reached.")
            break

        resolution += 32

        if resolution > 512:
            print("⚠ Max resolution hit.")
            break

    return verts, faces


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    verts, faces = generate_target_faces(100000)

    path = export_scad("frisbee_100k.scad", verts, faces)

    print("\n💾 Exported:", path)
    print("Final face count:", len(faces))
