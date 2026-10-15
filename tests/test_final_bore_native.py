"""Real STEP roundtrips and analytic counterexamples for isolated final bores."""
import json

import pytest

pytest.importorskip("build123d")

from test_final_bore_contract import probe
from test_final_geometry_native import _bore_program

from core.exact_build123d import Build123dBackend, Build123dCompileError
from core.final_geometry import evaluate_measurement, measure_bore
from core.requirement_ir import Requirement, RequirementIR, RequirementValue
from core.requirement_verification import ExactRequirementBinding, RequirementBindingSet, feature_ir_sha256, requirement_ir_sha256


def contract(program, p):
    source = "Keep the declared cylindrical hole."
    doc = RequirementIR(source=source, requirements=(Requirement(
        id="bore", kind="topology", strength="must", target="final_output", source_start=0,
        source_end=len(source), source_text=source, provenance="explicit",
        verification="geometric_relation", value=RequirementValue(1, "unitless")),))
    bindings = RequirementBindingSet(requirement_ir_sha256(doc), feature_ir_sha256(program),
        (ExactRequirementBinding("bore", program.outputs, "geometric_relation", p),))
    return doc, bindings


@pytest.mark.parametrize("mode", ["through", "unused", "filled", "blind"])
def test_exported_bore_contract(mode, tmp_path):
    program = _bore_program(mode)
    doc, bindings = contract(program, probe())
    backend = Build123dBackend()
    if mode != "through":
        with pytest.raises(Build123dCompileError):
            backend.export_verified_step(program, tmp_path / mode, requirements=doc, binding_set=bindings)
        assert not (tmp_path / mode).exists()
    else:
        receipt = backend.export_verified_step(program, tmp_path / mode, requirements=doc, binding_set=bindings)
        assert receipt.requirements_satisfied
        evidence = json.loads((tmp_path / mode / "requirements-verification.json").read_text(encoding="utf-8"))
        assert evidence["checks"][0]["basis"] == "exact_kernel_final_cylindrical_bore"


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("direction", [-1, 1])
def test_native_axes_and_wrong_location_radius_clearance(axis, direction, tmp_path):
    backend = Build123dBackend()
    bd = backend.bd
    angles = (0, 90, 0) if axis == "x" else (90, 0, 0) if axis == "y" else (0, 0, 0)
    index = ("x", "y", "z").index(axis)
    shape = bd.Box(20, 20, 20) - bd.Rot(*angles) * bd.Cylinder(3, 20)
    path = tmp_path / "shape.step"
    assert bd.export_step(shape, path)
    shape = bd.import_step(path)
    entry = [0., 0., 0.]
    entry[index] = -direction * 10
    p = {**probe(), "axis": axis, "direction": direction, "entry_mm": entry, "depth_mm": 20}
    assert evaluate_measurement(p, measure_bore(shape, bd, p))
    shifted = list(entry)
    shifted[(index + 1) % 3] += 2
    for wrong in [{**p, "entry_mm": shifted}, {**p, "radius_mm": 2}, {**p, "radius_mm": 4},
                  {**p, "depth_mm": 19}, {**p, "clearance_mm": 12}]:
        assert not evaluate_measurement(wrong, measure_bore(shape, bd, wrong))


def test_native_blind_end_and_intersecting_bore(tmp_path):
    backend = Build123dBackend()
    bd = backend.bd
    program = _bore_program("blind")
    p = {**probe(), "entry_mm": [0, 0, 4], "direction": -1, "depth_mm": 4, "termination": "blind"}
    doc, bindings = contract(program, p)
    assert backend.export_verified_step(program, tmp_path / "blind", requirements=doc, binding_set=bindings).requirements_satisfied
    through = bd.Box(40, 30, 8) - bd.Cylinder(3, 8)
    assert not evaluate_measurement(p, measure_bore(through, bd, p))
    crossed = through - bd.Rot(0, 90, 0) * bd.Cylinder(2, 40)
    p = probe()
    assert not evaluate_measurement(p, measure_bore(crossed, bd, p))
    disconnected = through + bd.Pos(30, 0, 0) * bd.Box(2, 2, 2)
    with pytest.raises(ValueError, match="one"):
        measure_bore(disconnected, bd, p)
