"""Check actual hole-boundary distances, including unused single-grid margins."""

from itertools import pairwise

import pytest

from core.complex_shapes import build_complex_shape


@pytest.mark.parametrize("columns,rows", [(1, 1), (1, 2), (2, 1), (2, 2)])
@pytest.mark.parametrize("margin", [10, 20])
def test_grid_ligaments_use_actual_circle_boundaries(columns, rows, margin):
    width, height, radius, thickness = 100, 80, 5, 30
    xs = [0] if columns == 1 else [-width/2+margin, width/2-margin]
    ys = [0] if rows == 1 else [-height/2+margin, height/2-margin]
    x_distances = [width/2-abs(x)-radius for x in xs]
    y_distances = [height/2-abs(y)-radius for y in ys]
    x_distances += [right-left-2*radius for left, right in pairwise(xs)]
    y_distances += [upper-lower-2*radius for lower, upper in pairwise(ys)]
    report = build_complex_shape({
        "schema_version": "neurocad-complex-shape-request-v1", "shape": "perforated_plate",
        "parameters": {"width_mm": width, "height_mm": height, "thickness_mm": thickness,
                       "hole_diameter_mm": 2*radius, "columns": columns, "rows": rows,
                       "edge_margin_mm": margin},
    }).analysis["geometry"]
    expected_x, expected_y = min(x_distances), min(y_distances)
    assert report["minimum_x_ligament_mm"] == pytest.approx(expected_x, rel=1e-12, abs=1e-12)
    assert report["minimum_y_ligament_mm"] == pytest.approx(expected_y, rel=1e-12, abs=1e-12)
    assert report["minimum_geometric_feature_mm"] == min(thickness, expected_x, expected_y)
