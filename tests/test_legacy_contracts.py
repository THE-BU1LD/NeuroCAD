from __future__ import annotations

import numpy as np
import pytest

from pipeline_stage import PipelineStage
from surfaces import Bezier, Circle, Curve, Line, Surface, normalize
from vector_fields_engine import VectorFieldEngine


def test_abstract_geometry_contracts_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        Curve()
    with pytest.raises(TypeError):
        Surface()
    with pytest.raises(TypeError):
        PipelineStage()


def test_curve_inputs_fail_closed_and_valid_curves_are_sampled() -> None:
    with pytest.raises(ValueError, match="zero-length"):
        normalize([0, 0, 0])
    with pytest.raises(ValueError, match="at least 2"):
        Line([0, 0, 0], [1, 1, 1]).sample(1)
    with pytest.raises(ValueError, match="control point"):
        Bezier([])
    with pytest.raises(ValueError, match="plane"):
        Circle(1, "invalid")
    points = Line([0, 0, 0], [2, 4, 6]).sample(3)
    assert np.allclose(points[1], [1, 2, 3])


def test_vector_fields_validate_inputs_and_produce_finite_arrays() -> None:
    engine = VectorFieldEngine()
    with pytest.raises(ValueError, match="zero vector"):
        engine.create_uniform_field([0, 0, 0], 1)
    with pytest.raises(ValueError, match="positive integer"):
        engine.create_vortex_field(grid_size=0)
    field = engine.create_uniform_field([1, 0, 0], 2, grid_size=3)
    assert field.shape == (3, 3, 3, 3)
    assert np.allclose(field[..., 0], 2)
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    deformed = engine.deform_mesh(vertices, field, influence=0.5)
    assert np.allclose(deformed, [[1, 0, 0], [2, 1, 1]])
