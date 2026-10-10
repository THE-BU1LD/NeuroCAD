"""Self-intersection geometry must not depend on the length unit."""

import numpy as np
import pytest

from core.mesh_geometry import analyze_self_intersections

FACES = [[0, 1, 2], [3, 4, 5]]
CASES = [
    # Coplanar, disjoint triangles with overlapping axis-aligned boxes.
    ([[0, 0, 0], [2, 0, 0], [0, 2, 0], [2, 2, 0], [1.1, 2, 0], [2, 1.1, 0]], False),
    # Coplanar overlap.
    ([[0, 0, 0], [2, 0, 0], [0, 2, 0], [0.2, 0.2, 0], [1.2, 0.2, 0], [0.2, 1.2, 0]], True),
    # Transverse intersection.
    ([[-1, -1, 0], [1, -1, 0], [0, 1, 0], [0, 0, -1], [0, 0, 1], [0.5, 0, 0]], True),
    # Parallel, distinct planes.
    ([[0, 0, 0], [2, 0, 0], [0, 2, 0], [0, 0, 0.1], [2, 0, 0.1], [0, 2, 0.1]], False),
]


@pytest.mark.parametrize("vertices,expected", CASES)
@pytest.mark.parametrize("scale", [1e-180, 1e-8, 0.1, 1.0, 1e160])
def test_intersection_verdict_is_invariant_under_uniform_scale(vertices, expected, scale):
    points = np.asarray(vertices, dtype=float) * scale
    report = analyze_self_intersections(points, FACES)
    assert report["self_intersecting"] is expected
    assert report["scale_mm"] == pytest.approx(float(np.ptp(points, axis=0).max()), rel=1e-14, abs=0)
    assert report["candidate_pairs_tested"] in (0, 1)


def test_large_translation_does_not_overflow_bounding_box_midpoint():
    points = np.asarray(CASES[1][0], dtype=float) * 1e293 + 1e308
    with np.errstate(over="raise", invalid="raise"):
        report = analyze_self_intersections(points, FACES)
    assert report["self_intersecting"] is True
    assert np.isfinite(report["scale_mm"])


def test_unrepresentable_span_is_rejected_instead_of_reporting_clean_mesh():
    points = [[-1e308, 0, 0], [1e308, 0, 0], [0, 1, 0]]
    with pytest.raises(ValueError, match="span"):
        analyze_self_intersections(points, [[0, 1, 2]])


def test_zero_extent_remains_invalid():
    with pytest.raises(ValueError, match="span|degenerate"):
        analyze_self_intersections(np.zeros((3, 3)), [[0, 1, 2]])
