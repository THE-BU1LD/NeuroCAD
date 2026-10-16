"""Pure evidence-contract rejection controls; no native geometry is fabricated."""
from dataclasses import replace

import pytest
from test_final_geometry_requirements import Inspection, contract

from core.final_geometry import evaluate_measurement, probe_hash, validate_probe
from core.requirement_ir import RequirementValue
from core.requirement_verification import verify_exact_requirements


def probe():
    return {"kind": "output_cylindrical_hole", "axis": "z", "direction": 1,
            "entry_mm": [0, 0, -4], "radius_mm": 3, "depth_mm": 8,
            "termination": "through", "clearance_mm": 1, "tolerance_mm": 0.001,
            "volume_tolerance_mm3": 0.000001}


def measurement(p):
    return {"probe_sha256": probe_hash(p), "entry_error_mm": 0., "terminal_error_mm": 0.,
            "void_material_mm3": 0., "sleeve_missing_mm3": 0., "cap_missing_mm3": 0.,
            "valid_brep": True, "manifold": True, "solid_count": 1}


@pytest.mark.parametrize("key,value", [("axis", "diagonal"), ("direction", True), ("direction", 0),
    ("entry_mm", [0, 0]), ("entry_mm", [0, True, 0]), ("radius_mm", 0),
    ("depth_mm", float("inf")), ("tolerance_mm", 1), ("clearance_mm", -1),
    ("volume_tolerance_mm3", 100), ("termination", "unknown"), ("radius_mm", 10**400)])
def test_reject_invalid_probe(key, value):
    with pytest.raises((ValueError, TypeError)):
        validate_probe({**probe(), key: value})


@pytest.mark.parametrize("key", ["void_material_mm3", "sleeve_missing_mm3", "cap_missing_mm3",
                                "entry_error_mm", "terminal_error_mm"])
def test_geometric_residuals_cannot_pass(key):
    p = probe()
    assert evaluate_measurement(p, measurement(p))
    assert not evaluate_measurement(p, {**measurement(p), key: 1})
    for invalid in [-1, True, float("nan")]:
        with pytest.raises((ValueError, TypeError)):
            evaluate_measurement(p, {**measurement(p), key: invalid})


def test_missing_stale_and_forged_evidence_refused():
    p = probe()
    for evidence in [{}, {**measurement(p), "probe_sha256": "0" * 64},
                     {**measurement(p), "solid_count": True}, {**measurement(p), "valid_brep": 1}]:
        with pytest.raises((ValueError, TypeError)):
            evaluate_measurement(p, evidence)
    with pytest.raises((ValueError, TypeError)):
        evaluate_measurement({**p, "entry_mm": [1, 0, -4]}, measurement(p))


def test_requirement_requires_final_measurement_and_output_scope():
    doc, program, bindings = contract("output_cylindrical_hole", RequirementValue(1, "unitless"))
    p = probe()
    bindings = replace(bindings, bindings=(replace(bindings.bindings[0], probe=p),))
    assert not verify_exact_requirements(doc, program, Inspection(), bindings).satisfied_for_all_must
    result = verify_exact_requirements(doc, program, Inspection(), bindings,
                                      final_geometry_measurements={"aggregate": measurement(p)})
    assert result.satisfied_for_all_must
    bad = replace(bindings, bindings=(replace(bindings.bindings[0], feature_ids=("unused_tool",)),))
    assert not verify_exact_requirements(doc, program, Inspection(), bad,
        final_geometry_measurements={"aggregate": measurement(p)}).satisfied_for_all_must


def test_pinned_kernel_empty_intersection_contract():
    from types import SimpleNamespace

    from core.final_geometry import _residual_volume

    assert _residual_volume(None, empty_intersection=True) == 0
    assert _residual_volume(SimpleNamespace(volume=2)) == 2
    with pytest.raises(ValueError, match="Missing"):
        _residual_volume(None)
    with pytest.raises(ValueError):
        _residual_volume(SimpleNamespace(volume=float("nan")))
