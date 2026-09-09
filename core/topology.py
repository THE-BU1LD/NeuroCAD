"""Combinatorial topology of finite triangular complexes, with F2 coefficients.

This analyzes connectivity, not self-intersections, geometric equivalence, or
physical fit. Surface classification is reported only after edge AND vertex-link
manifold checks. See docs/MATHEMATICS.md for definitions and limits.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

MAX_TOPOLOGY_FACES = 100_000
MAX_TOPOLOGY_VERTICES = 300_000
MAX_SINGULAR_GENERATORS = 4096


class _UnionFind:
    def __init__(self, count: int):
        self.parents = list(range(count))
        self.sizes = [1] * count

    def find(self, item: int) -> int:
        while self.parents[item] != item:
            self.parents[item] = self.parents[self.parents[item]]
            item = self.parents[item]
        return item

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left == right:
            return
        if self.sizes[left] < self.sizes[right]:
            left, right = right, left
        self.parents[right] = left
        self.sizes[left] += self.sizes[right]


def _rank_f2(rows: list[int]) -> int:
    """Exact binary Gaussian elimination, with integer bitsets as rows."""
    pivots: dict[int, int] = {}
    for row in rows:
        while row:
            pivot = row.bit_length() - 1
            if pivot in pivots:
                row ^= pivots[pivot]
            else:
                pivots[pivot] = row
                break
    return len(pivots)


def _link_is_manifold(edges: list[tuple[int, int]]) -> bool:
    if not edges:
        return False
    adjacency: dict[int, list[int]] = defaultdict(list)
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    degrees = [len(neighbors) for neighbors in adjacency.values()]
    if any(degree not in (1, 2) for degree in degrees) or degrees.count(1) not in (0, 2):
        return False
    seen: set[int] = set()
    queue = [next(iter(adjacency))]
    while queue:
        vertex = queue.pop()
        if vertex not in seen:
            seen.add(vertex)
            queue.extend(neighbor for neighbor in adjacency[vertex] if neighbor not in seen)
    return len(seen) == len(adjacency)


def analyze_triangle_complex(vertices: Any, faces: Any) -> dict[str, Any]:
    """Compute Betti numbers, singularities and compact-surface classification.

    Vertex indices define connectivity; coordinates are not merged or repaired.
    Isolated vertices count towards b0 and make the complex non-surface. Duplicate
    triangles and zero-area/non-finite geometry are invalid inputs, not repaired.
    """
    points = np.asarray(vertices)
    triangles = np.asarray(faces)
    if points.ndim != 2 or points.shape[1] != 3 or not 1 <= len(points) <= MAX_TOPOLOGY_VERTICES:
        raise ValueError(f"vertices must be an N x 3 array with 1..{MAX_TOPOLOGY_VERTICES} vertices")
    if points.dtype.kind not in "iuf" or not np.isfinite(points).all():
        raise ValueError("vertices must contain finite real coordinates")
    if triangles.ndim != 2 or triangles.shape[1] != 3 or not 1 <= len(triangles) <= MAX_TOPOLOGY_FACES:
        raise ValueError(f"faces must be an M x 3 array with 1..{MAX_TOPOLOGY_FACES} triangles")
    if triangles.dtype.kind not in "iu" or (triangles < 0).any() or (triangles >= len(points)).any():
        raise ValueError("faces must contain valid integer vertex indices")
    points = points.astype(float)
    # Scaling before subtraction avoids overflow and preserves degeneracy.
    scale = max(1.0, float(np.abs(points).max()))
    normalized = points / scale
    coords = normalized[triangles]
    area_vectors = np.cross(coords[:, 1] - coords[:, 0], coords[:, 2] - coords[:, 0])
    if not np.isfinite(area_vectors).all() or (np.max(np.abs(area_vectors), axis=1) == 0).any():
        raise ValueError("faces contain degenerate or numerically unresolvable triangles")
    if len(np.unique(np.sort(triangles, axis=1), axis=0)) != len(triangles):
        raise ValueError("duplicate triangles do not define a simplicial complex")

    v_count, f_count = len(points), len(triangles)
    vertex_sets, face_sets = _UnionFind(v_count), _UnionFind(f_count)
    edge_faces: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    links: list[list[tuple[int, int]]] = [[] for _ in range(v_count)]
    for index, face in enumerate(triangles):
        a, b, c = (int(value) for value in face)
        vertex_sets.union(a, b)
        vertex_sets.union(a, c)
        for vertex, left, right in ((a, b, c), (b, c, a), (c, a, b)):
            links[vertex].append((left, right))
        for left, right in ((a, b), (b, c), (c, a)):
            edge_faces[min(left, right), max(left, right)].append((index, 1 if left < right else -1))

    dual: list[list[tuple[int, bool]]] = [[] for _ in range(f_count)]
    for incidence in edge_faces.values():
        if len(incidence) == 2:
            (left, sign_left), (right, sign_right) = incidence
            face_sets.union(left, right)
            different = sign_left == sign_right
            dual[left].append((right, different))
            dual[right].append((left, different))

    # ker(d2): each two-face edge equates coefficients; a boundary edge sets
    # its face-group coefficient to zero. Only singular edges need elimination.
    zero_groups = {face_sets.find(incidence[0][0]) for incidence in edge_faces.values() if len(incidence) == 1}
    free_groups = sorted({face_sets.find(index) for index in range(f_count)} - zero_groups)
    singular_edges = [edge for edge, incidence in edge_faces.items() if len(incidence) > 2]
    if singular_edges and len(free_groups) > MAX_SINGULAR_GENERATORS:
        raise ValueError(f"singular-complex reduction exceeds {MAX_SINGULAR_GENERATORS} generators")
    group_index = {group: index for index, group in enumerate(free_groups)}
    rows = []
    for edge in singular_edges:
        row = 0
        for face, _ in edge_faces[edge]:
            group = face_sets.find(face)
            if group in group_index:
                row ^= 1 << group_index[group]
        rows.append(row)
    b2 = len(free_groups) - _rank_f2(rows)
    roots = [vertex_sets.find(vertex) for vertex in range(v_count)]
    b0 = len(set(roots))
    e_count = len(edge_faces)
    rank_d2 = f_count - b2
    b1 = e_count - v_count + b0 - rank_d2

    bad_vertices = [vertex for vertex, link in enumerate(links) if not _link_is_manifold(link)]
    bad_roots = {roots[vertex] for vertex in bad_vertices}
    bad_roots.update(roots[edge[0]] for edge in singular_edges)
    boundary_edges = [edge for edge, incidence in edge_faces.items() if len(incidence) == 1]
    boundary_sets = _UnionFind(v_count)
    for left, right in boundary_edges:
        boundary_sets.union(left, right)
    boundary_roots: dict[int, set[int]] = defaultdict(set)
    for left, _ in boundary_edges:
        boundary_roots[roots[left]].add(boundary_sets.find(left))

    flips: dict[int, bool] = {}
    nonorientable_roots: set[int] = set()
    for face in range(f_count):
        if face in flips:
            continue
        flips[face] = False
        queue = [face]
        while queue:
            current = queue.pop()
            for neighbor, different in dual[current]:
                target_flip = flips[current] ^ different
                if neighbor in flips:
                    if flips[neighbor] != target_flip:
                        nonorientable_roots.add(roots[int(triangles[current, 0])])
                else:
                    flips[neighbor] = target_flip
                    queue.append(neighbor)

    counts: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])
    for root in roots:
        counts[root][0] += 1
    for left, _ in edge_faces:
        counts[roots[left]][1] += 1
    for face in triangles:
        counts[roots[int(face[0])]][2] += 1
    components = []
    for root, (vertices_n, edges_n, faces_n) in sorted(counts.items()):
        chi = vertices_n - edges_n + faces_n
        manifold = root not in bad_roots
        orientable = root not in nonorientable_roots if manifold else None
        loops = len(boundary_roots[root]) if manifold else None
        genus = (2 - int(loops or 0) - chi) // 2 if orientable else None
        components.append({
            "vertices": vertices_n, "edges": edges_n, "faces": faces_n,
            "euler_characteristic": chi, "manifold": manifold,
            "orientable": orientable, "boundary_loops": loops, "genus": genus,
            "crosscap_number": 2 - int(loops or 0) - chi if orientable is False else None,
        })
    return {
        "schema_version": "neurocad-topology-v1", "coefficient_field": "F2",
        "vertices": v_count, "edges": e_count, "faces": f_count,
        "euler_characteristic": v_count - e_count + f_count,
        "betti_numbers": [b0, b1, b2],
        "boundary_ranks": [v_count - b0, rank_d2],
        "manifold": not bad_roots, "closed": not boundary_edges,
        "boundary_edges": len(boundary_edges), "nonmanifold_edges": len(singular_edges),
        "nonmanifold_vertices": len(bad_vertices), "nonmanifold_vertex_examples": bad_vertices[:32],
        "components": components,
        "limitations": [
            "Connectivity of supplied vertex indices only; no self-intersection or embedding proof.",
            "F2 homology does not determine geometric equivalence, dimensions, material strength, or physical fit.",
        ],
    }
