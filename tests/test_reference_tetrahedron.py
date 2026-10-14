"""Closed-form checks for the independent mesh-volume reference calculation."""
from __future__ import annotations

import pytest

from scripts.reproduce_mesh_quality import signed_tetra_volume


def test_analytic_tetrahedron_and_translation():
    points = [[0., 0., 0.], [2., 0., 0.], [0., 3., 0.], [0., 0., 4.]]
    assert signed_tetra_volume(points) == 4.0
    translated = [[coordinate + 100 for coordinate in point] for point in points]
    assert signed_tetra_volume(translated) == pytest.approx(4.0)


def test_inverted_and_degenerate_tetrahedra_have_nonpositive_signed_volume():
    assert signed_tetra_volume([[0., 0., 0.], [0., 3., 0.], [2., 0., 0.], [0., 0., 4.]]) == -4.0
    assert signed_tetra_volume([[0., 0., 0.], [2., 0., 0.], [0., 3., 0.], [2., 3., 0.]]) == 0.0
