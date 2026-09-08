from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
import trimesh

from core.artifacts import verify_stl
from core.topology import analyze_triangle_complex


def _torus() -> tuple[list, list]:
    count = 8
    vertices = []
    for i in range(count):
        u = math.tau * i / count
        for j in range(count):
            v = math.tau * j / count
            vertices.append([(3 + math.cos(v)) * math.cos(u), (3 + math.cos(v)) * math.sin(u), math.sin(v)])
    faces = []
    for i in range(count):
        for j in range(count):
            a, b = i * count + j, ((i + 1) % count) * count + j
            c, d = ((i + 1) % count) * count + (j + 1) % count, i * count + (j + 1) % count
            faces.extend([(a, b, c), (a, c, d)])
    return vertices, faces


def _mobius() -> tuple[list, list]:
    vertices = []
    count = 12
    for i in range(count):
        u = math.tau * i / count
        for width in (-0.3, 0.3):
            vertices.append([(2 + width * math.cos(u / 2)) * math.cos(u),
                             (2 + width * math.cos(u / 2)) * math.sin(u), width * math.sin(u / 2)])
    faces = []
    for i in range(count):
        a, d = i * 2, i * 2 + 1
        b, c = (i + 1) * 2, (i + 1) * 2 + 1
        if i == count - 1:
            b, c = 1, 0
        faces.extend([(a, b, c), (a, c, d)])
    return vertices, faces


def test_sphere_and_torus_have_different_homology() -> None:
    sphere = trimesh.creation.icosphere(subdivisions=1)
    report = analyze_triangle_complex(sphere.vertices, sphere.faces)
    assert report["betti_numbers"] == [1, 0, 1]
    assert report["components"][0]["genus"] == 0
    vertices, faces = _torus()
    report = analyze_triangle_complex(vertices, faces)
    assert report["betti_numbers"] == [1, 2, 1]
    assert report["components"][0]["genus"] == 1
    assert report["components"][0]["orientable"] is True
    assert report["closed"] and report["manifold"]


def test_disk_boundary_and_mobius_nonorientability() -> None:
    disk = analyze_triangle_complex([[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 1, 2]])
    assert disk["betti_numbers"] == [1, 0, 0]
    assert disk["components"][0]["boundary_loops"] == 1
    vertices, faces = _mobius()
    mobius = analyze_triangle_complex(vertices, faces)
    assert mobius["betti_numbers"] == [1, 1, 0]
    assert mobius["components"][0]["boundary_loops"] == 1
    assert mobius["components"][0]["orientable"] is False
    assert mobius["components"][0]["genus"] is None
    assert mobius["components"][0]["crosscap_number"] == 1


def test_winding_reversal_does_not_change_orientability_or_betti_numbers() -> None:
    vertices, faces = _torus()
    altered = [face[::-1] if index % 3 else face for index, face in enumerate(faces)]
    assert analyze_triangle_complex(vertices, faces) == analyze_triangle_complex(vertices, altered)


def test_disconnected_and_isolated_vertices_are_counted() -> None:
    points = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [10, 0, 0], [11, 0, 0], [10, 1, 0], [20, 0, 0]]
    report = analyze_triangle_complex(points, [[0, 1, 2], [3, 4, 5]])
    assert report["betti_numbers"] == [3, 0, 0]
    assert report["nonmanifold_vertices"] == 1
    assert not report["manifold"]


def test_pinched_surface_has_singular_vertex_despite_manifold_edges(tmp_path: Path) -> None:
    vertices, faces = _torus()
    vertices[36] = vertices[0]
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.is_volume
    report = analyze_triangle_complex(mesh.vertices, mesh.faces)
    assert report["nonmanifold_edges"] == 0
    assert report["nonmanifold_vertices"] == 1
    assert not report["manifold"]
    path = tmp_path / "pinched.stl"
    mesh.export(path)
    with pytest.raises(RuntimeError, match="non-manifold vertex"):
        verify_stl(path)


def _dense_rank_f2(matrix: np.ndarray) -> int:
    matrix = matrix.copy()
    rank = 0
    for column in range(matrix.shape[1]):
        pivot = next((row for row in range(rank, len(matrix)) if matrix[row, column]), None)
        if pivot is None:
            continue
        matrix[[rank, pivot]] = matrix[[pivot, rank]]
        for row in range(rank + 1, len(matrix)):
            if matrix[row, column]:
                matrix[row] ^= matrix[rank]
        rank += 1
    return rank


def test_singular_complex_matches_independent_boundary_matrix_reduction() -> None:
    # Random subcomplexes of the 2-skeleton on seven vertices include branching
    # edges, closed cycles, and vertices with disconnected links.
    from itertools import combinations
    rng = np.random.default_rng(1729)
    points = rng.normal(size=(7, 3))
    all_faces = list(combinations(range(7), 3))
    for _ in range(20):
        faces = [face for face in all_faces if rng.random() < 0.5]
        edges = sorted({tuple(sorted(edge)) for face in faces for edge in combinations(face, 2)})
        boundary1 = np.zeros((7, len(edges)), dtype=np.uint8)
        boundary2 = np.zeros((len(edges), len(faces)), dtype=np.uint8)
        for index, (a, b) in enumerate(edges):
            boundary1[a, index] = boundary1[b, index] = 1
        for index, face in enumerate(faces):
            for edge in combinations(face, 2):
                boundary2[edges.index(tuple(sorted(edge))), index] = 1
        assert not ((boundary1 @ boundary2) % 2).any()
        r1, r2 = _dense_rank_f2(boundary1), _dense_rank_f2(boundary2)
        report = analyze_triangle_complex(points, faces)
        assert report["betti_numbers"] == [7 - r1, len(edges) - r1 - r2, len(faces) - r2]


@pytest.mark.parametrize("faces", [[[0, 0, 1]], [[0, 1, 3]], [[0.0, 1.0, 2.0]], [[0, 1, 2], [2, 1, 0]]])
def test_invalid_triangles_fail_closed(faces: list) -> None:
    with pytest.raises(ValueError):
        analyze_triangle_complex([[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces)


def test_cli_topology_writes_report_and_refuses_clobber(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from neurocad_cli import build_parser
    path, output = tmp_path / "torus.stl", tmp_path / "report.json"
    trimesh.Trimesh(*_torus(), process=False).export(path)
    parser = build_parser()
    args = parser.parse_args(["topology", str(path), "-o", str(output)])
    assert args.func(args) == 0
    assert json.loads(output.read_text())["betti_numbers"] == [1, 2, 1]
    with pytest.raises(FileExistsError):
        args.func(args)
    assert path.is_file()
