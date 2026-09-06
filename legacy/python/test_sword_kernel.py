import numpy as np
from cad_intelligence_core_allinone import UniversalCADCoreV3


# =========================
# SWORD SDF
# =========================

def box_sdf(p, size):
    q = np.abs(p) - size
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.max(q, axis=-1), 0)


def cylinder_sdf(p, r, h):
    d = np.stack([
        np.linalg.norm(p[..., :2], axis=-1) - r,
        np.abs(p[..., 2]) - h/2
    ], axis=-1)
    return np.minimum(np.maximum(d[...,0], d[...,1]), 0) + np.linalg.norm(np.maximum(d,0), axis=-1)


def taper_blade(p, length=2.5, base_w=0.28, tip_w=0.06, thickness=0.05):
    z = p[...,2]
    t = np.clip((z + length/2) / length, 0, 1)
    w = base_w*(1-t) + tip_w*t

    size = np.stack([
        w,
        np.full_like(w, thickness),
        np.full_like(w, length/2)
    ], axis=-1)

    return box_sdf(p, size)


def sword_sdf(p):

    # blade
    blade = taper_blade(p - np.array([0,0,0.6]))

    # fuller groove
    fuller = cylinder_sdf(p - np.array([0,0,0.6]), 0.05, 1.8)
    blade = np.maximum(blade, -fuller)

    # guard
    guard = box_sdf(p - np.array([0,0,-0.7]), np.array([0.55, 0.12, 0.08]))

    # grip
    grip = cylinder_sdf(p - np.array([0,0,-1.3]), 0.12, 0.9)

    # pommel
    pommel = cylinder_sdf(p - np.array([0,0,-1.9]), 0.18, 0.3)

    return np.minimum(
        np.minimum(blade, guard),
        np.minimum(grip, pommel)
    )


# =========================
# RUN TEST
# =========================

print("\n[SWORD TEST] Generating implicit sword...\n")

core = UniversalCADCoreV3()

# ✅ Updated API: grid now returns origin
grid, spacing, origin = core.sdf.grid(
    sword_sdf,
    bounds=2.6,
    res=96
)

# ✅ Pass origin directly from grid
verts, faces, normals = core.mc.extract(
    grid,
    spacing=spacing,
    origin=origin,
    refine=True,
    return_normals=True
)

file = core.exporter.export(verts, faces, filename="sword.scad")

print("Vertices:", len(verts))
print("Faces:", len(faces))
print("Exported:", file)
print("\nOpen sword.scad in OpenSCAD.\n")
