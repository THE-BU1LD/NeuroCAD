# geometry_metrics.py

import trimesh


def triangle_count(mesh: trimesh.Trimesh) -> int:
    return len(mesh.faces)


def bounding_box_volume(mesh: trimesh.Trimesh) -> float:
    bounds = mesh.bounds
    extents = bounds[1] - bounds[0]
    return extents[0] * extents[1] * extents[2]


def complexity_score(mesh: trimesh.Trimesh) -> float:
    return triangle_count(mesh) / (bounding_box_volume(mesh) + 1e-6)
