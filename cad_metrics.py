import numpy as np

def surface_error(phi_func, verts):
    return np.mean(np.abs(phi_func(verts)))

def normal_deviation(mesh_normals, sdf_normals):
    dots = np.sum(mesh_normals*sdf_normals, axis=1)
    dots = np.clip(dots, -1, 1)
    angles = np.degrees(np.arccos(dots))
    return np.mean(angles)

def edge_sharpness(normals, faces):
    n0 = normals[faces[:,0]]
    n1 = normals[faces[:,1]]
    n2 = normals[faces[:,2]]

    d01 = np.linalg.norm(n0-n1, axis=1)
    d12 = np.linalg.norm(n1-n2, axis=1)
    d20 = np.linalg.norm(n2-n0, axis=1)

    return np.mean(np.maximum.reduce([d01,d12,d20]))
