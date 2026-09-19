"""Bounded geometric checks for finite triangle meshes.

These checks complement, rather than replace, the combinatorial invariants in
``core.topology``.  They deliberately report the numerical tolerance and search
limits used so a successful result is not mistaken for an exact BREP proof.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

MAX_INTERSECTION_CANDIDATES = 2_000_000
MAX_REPORTED_INTERSECTIONS = 32


def _orient2d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _point_on_segment_2d(point: np.ndarray, left: np.ndarray, right: np.ndarray, epsilon: float) -> bool:
    return (
        abs(_orient2d(left, right, point)) <= epsilon
        and min(left[0], right[0]) - epsilon <= point[0] <= max(left[0], right[0]) + epsilon
        and min(left[1], right[1]) - epsilon <= point[1] <= max(left[1], right[1]) + epsilon
    )


def _segments_intersect_2d(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    d: np.ndarray,
    epsilon: float,
) -> bool:
    o1, o2 = _orient2d(a, b, c), _orient2d(a, b, d)
    o3, o4 = _orient2d(c, d, a), _orient2d(c, d, b)
    if ((o1 > epsilon and o2 < -epsilon) or (o1 < -epsilon and o2 > epsilon)) and (
        (o3 > epsilon and o4 < -epsilon) or (o3 < -epsilon and o4 > epsilon)
    ):
        return True
    return any(
        (
            abs(orientation) <= epsilon
            and _point_on_segment_2d(point, left, right, epsilon)
        )
        for orientation, point, left, right in (
            (o1, c, a, b),
            (o2, d, a, b),
            (o3, a, c, d),
            (o4, b, c, d),
        )
    )


def _point_in_triangle_2d(point: np.ndarray, triangle: np.ndarray, epsilon: float) -> bool:
    orientations = [_orient2d(triangle[index], triangle[(index + 1) % 3], point) for index in range(3)]
    return not (any(value > epsilon for value in orientations) and any(value < -epsilon for value in orientations))


def _coplanar_triangles_intersect(
    left: np.ndarray,
    right: np.ndarray,
    normal: np.ndarray,
    epsilon: float,
) -> bool:
    # Drop the coordinate where the plane normal is strongest. This maximizes
    # the projected triangle area and avoids an arbitrary XY-only assumption.
    projection = [axis for axis in range(3) if axis != int(np.argmax(np.abs(normal)))]
    left_2d, right_2d = left[:, projection], right[:, projection]
    for left_index in range(3):
        for right_index in range(3):
            if _segments_intersect_2d(
                left_2d[left_index],
                left_2d[(left_index + 1) % 3],
                right_2d[right_index],
                right_2d[(right_index + 1) % 3],
                epsilon,
            ):
                return True
    return _point_in_triangle_2d(left_2d[0], right_2d, epsilon) or _point_in_triangle_2d(
        right_2d[0], left_2d, epsilon
    )


def _segment_intersects_triangle(
    start: np.ndarray,
    end: np.ndarray,
    triangle: np.ndarray,
    epsilon: float,
) -> bool:
    direction = end - start
    edge1, edge2 = triangle[1] - triangle[0], triangle[2] - triangle[0]
    cross = np.cross(direction, edge2)
    determinant = float(np.dot(edge1, cross))
    determinant_scale = float(np.linalg.norm(edge1) * np.linalg.norm(edge2) * np.linalg.norm(direction))
    if determinant_scale == 0.0 or abs(determinant) <= epsilon * determinant_scale:
        return False
    inverse = 1.0 / determinant
    offset = start - triangle[0]
    u = inverse * float(np.dot(offset, cross))
    if u < -epsilon or u > 1.0 + epsilon:
        return False
    q = np.cross(offset, edge1)
    v = inverse * float(np.dot(direction, q))
    if v < -epsilon or u + v > 1.0 + epsilon:
        return False
    distance = inverse * float(np.dot(edge2, q))
    return -epsilon <= distance <= 1.0 + epsilon


def _triangles_intersect(left: np.ndarray, right: np.ndarray, epsilon: float) -> bool:
    left_normal = np.cross(left[1] - left[0], left[2] - left[0])
    right_normal = np.cross(right[1] - right[0], right[2] - right[0])
    left_normal_length = float(np.linalg.norm(left_normal))
    right_normal_length = float(np.linalg.norm(right_normal))
    if left_normal_length == 0.0 or right_normal_length == 0.0:
        return False
    right_to_left_plane = ((right - left[0]) @ left_normal) / left_normal_length
    left_to_right_plane = ((left - right[0]) @ right_normal) / right_normal_length
    if np.all(right_to_left_plane > epsilon) or np.all(right_to_left_plane < -epsilon):
        return False
    if np.all(left_to_right_plane > epsilon) or np.all(left_to_right_plane < -epsilon):
        return False
    if np.all(np.abs(right_to_left_plane) <= epsilon) and np.all(np.abs(left_to_right_plane) <= epsilon):
        return _coplanar_triangles_intersect(left, right, left_normal, epsilon)
    for index in range(3):
        if _segment_intersects_triangle(left[index], left[(index + 1) % 3], right, epsilon):
            return True
        if _segment_intersects_triangle(right[index], right[(index + 1) % 3], left, epsilon):
            return True
    return False


def analyze_self_intersections(
    vertices: Any,
    faces: Any,
    *,
    relative_tolerance: float = 1e-12,
    max_candidate_pairs: int = MAX_INTERSECTION_CANDIDATES,
    max_reported: int = MAX_REPORTED_INTERSECTIONS,
) -> dict[str, Any]:
    """Find intersections between triangles that share no indexed vertex.

    A sweep-and-prune broad phase bounds work for ordinary tessellated solids.
    The function fails closed when overlapping AABBs exceed the declared search
    budget instead of silently returning a partial success result.
    """

    points = np.asarray(vertices)
    triangles = np.asarray(faces)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 3:
        raise ValueError("vertices must be an N x 3 array with at least three vertices")
    if points.dtype.kind not in "iuf" or not np.isfinite(points).all():
        raise ValueError("vertices must contain finite real coordinates")
    if triangles.ndim != 2 or triangles.shape[1] != 3 or len(triangles) < 1:
        raise ValueError("faces must be an M x 3 array with at least one triangle")
    if triangles.dtype.kind not in "iu" or (triangles < 0).any() or (triangles >= len(points)).any():
        raise ValueError("faces must contain valid integer vertex indices")
    if isinstance(relative_tolerance, bool) or not isinstance(relative_tolerance, (int, float)):
        raise TypeError("relative_tolerance must be a finite non-negative number")
    tolerance = float(relative_tolerance)
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("relative_tolerance must be a finite non-negative number")
    if isinstance(max_candidate_pairs, bool) or not isinstance(max_candidate_pairs, int) or max_candidate_pairs < 1:
        raise ValueError("max_candidate_pairs must be a positive integer")
    if isinstance(max_reported, bool) or not isinstance(max_reported, int) or max_reported < 1:
        raise ValueError("max_reported must be a positive integer")

    points = points.astype(float)
    span = np.ptp(points, axis=0)
    scale = max(1.0, float(np.max(span)))
    normalized = (points - (np.min(points, axis=0) + np.max(points, axis=0)) / 2.0) / scale
    geometry = normalized[triangles]
    normals = np.cross(geometry[:, 1] - geometry[:, 0], geometry[:, 2] - geometry[:, 0])
    if (np.max(np.abs(normals), axis=1) == 0).any():
        raise ValueError("faces contain degenerate or numerically unresolvable triangles")

    minimums, maximums = geometry.min(axis=1), geometry.max(axis=1)
    sweep_axis = int(np.argmax(np.ptp((minimums + maximums) / 2.0, axis=0)))
    remaining_axes = [axis for axis in range(3) if axis != sweep_axis]
    order = np.argsort(minimums[:, sweep_axis], kind="stable")
    ordered_minimums = minimums[order, sweep_axis]
    candidate_pairs = 0
    intersections: list[list[int]] = []
    truncated = False

    for position, left_index_value in enumerate(order):
        left_index = int(left_index_value)
        stop = int(
            np.searchsorted(
                ordered_minimums,
                maximums[left_index, sweep_axis] + tolerance,
                side="right",
            )
        )
        if stop <= position + 1:
            continue
        possible = order[position + 1 : stop]
        overlaps = np.ones(len(possible), dtype=bool)
        for axis in remaining_axes:
            overlaps &= maximums[possible, axis] + tolerance >= minimums[left_index, axis]
            overlaps &= minimums[possible, axis] - tolerance <= maximums[left_index, axis]
        for right_index_value in possible[overlaps]:
            right_index = int(right_index_value)
            if {int(value) for value in triangles[left_index]} & {int(value) for value in triangles[right_index]}:
                continue
            candidate_pairs += 1
            if candidate_pairs > max_candidate_pairs:
                raise ValueError(
                    f"self-intersection broad phase exceeds {max_candidate_pairs} non-adjacent candidate pairs"
                )
            if _triangles_intersect(geometry[left_index], geometry[right_index], tolerance):
                intersections.append([min(left_index, right_index), max(left_index, right_index)])
                if len(intersections) >= max_reported:
                    truncated = True
                    break
        if truncated:
            break

    intersections.sort()
    return {
        "schema_version": "neurocad-self-intersection-v1",
        "self_intersecting": bool(intersections),
        "intersection_pairs": intersections,
        "reported_intersections_truncated": truncated,
        "candidate_pairs_tested": candidate_pairs,
        "relative_tolerance": tolerance,
        "scale_mm": scale,
        "limitations": [
            "Floating-point triangle tests are scale-normalized but are not an exact-arithmetic BREP proof.",
            "Pairs sharing an indexed vertex are excluded; the check targets non-adjacent triangle intersections.",
        ],
    }
