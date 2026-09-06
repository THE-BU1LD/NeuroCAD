import numpy as np
from cad_master_kernel import UniversalCADCoreV4
from differential_geometry import SmoothBoolean, DeformationField


# ============================================
# BASIC SDF PRIMITIVES
# ============================================

def box_sdf(p, size):
    q = np.abs(p) - size
    return np.linalg.norm(np.maximum(q,0), axis=-1) + \
           np.minimum(np.max(q,axis=-1),0)

def cylinder_sdf(p, r, h):
    d = np.stack([
        np.linalg.norm(p[...,:2],axis=-1)-r,
        np.abs(p[...,2])-h/2
    ], -1)
    return np.minimum(np.maximum(d[...,0],d[...,1]),0) + \
           np.linalg.norm(np.maximum(d,0),axis=-1)

def taper_blade(p, L=2.6, base=0.28, tip=0.06, t=0.05):
    z = p[...,2]
    u = np.clip((z+L/2)/L,0,1)
    w = base*(1-u)+tip*u
    size = np.stack([w, np.full_like(w,t), np.full_like(w,L/2)],-1)
    return box_sdf(p,size)


# ============================================
# ADVANCED SWORD
# ============================================

blend = SmoothBoolean()
deform = DeformationField()

def sword_sdf(p):

    p = deform.twist(p, strength=1.2)

    blade = taper_blade(p - np.array([0,0,0.6]))
    fuller = cylinder_sdf(p - np.array([0,0,0.6]), 0.05, 1.8)
    blade = blend.smooth_subtraction(blade, fuller, 0.08)

    guard = box_sdf(p - np.array([0,0,-0.7]),
                    np.array([0.55,0.12,0.08]))

    grip = cylinder_sdf(p - np.array([0,0,-1.3]), 0.12, 0.9)
    pommel = cylinder_sdf(p - np.array([0,0,-1.9]), 0.18, 0.3)

    body = blend.smooth_union(blade, guard, 0.2)
    body = blend.smooth_union(body, grip, 0.2)
    body = blend.smooth_union(body, pommel, 0.2)

    return body


# ============================================
# RUN TEST
# ============================================

print("\n[ADVANCED TEST] Building sword...\n")

core = UniversalCADCoreV4()

result = core.build(
    sword_sdf,
    bounds=2.8,
    res=110,
    scad_path="advanced_sword.scad"
)

print(result)
print("\nOpen advanced_sword.scad in OpenSCAD\n")
