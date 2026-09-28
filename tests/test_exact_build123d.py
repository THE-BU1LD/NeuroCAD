from __future__ import annotations

import hashlib
import json
import math

import pytest

pytest.importorskip("build123d")

from core.exact_build123d import Build123dBackend, Build123dCompileError
from core.feature_ir import DesignParameter, EntitySelector, Feature, FeatureProgram
from core.requirement_ir import (
    Requirement,
    RequirementIR,
    RequirementValue,
    serialize_requirement_ir_json,
)
from core.requirement_verification import (
    ExactRequirementBinding,
    RequirementBindingSet,
    feature_ir_sha256,
    requirement_ir_sha256,
    serialize_binding_set_json,
    verify_unchanged_must_requirements,
)


def _program(*features: Feature, output: str) -> FeatureProgram:
    return FeatureProgram(
        title="build123d golden fixture",
        parameters=(),
        features=features,
        outputs=(output,),
        metadata={"fixture": output},
    )


def test_build123d_compiles_exact_box() -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        output="body",
    )
    receipt = Build123dBackend().build_receipt(program)
    assert receipt.inspection.valid_brep
    assert receipt.inspection.manifold
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((40.0, 30.0, 20.0), abs=1e-8)
    assert receipt.inspection.volume_mm3 == pytest.approx(24000.0, rel=1e-10)


def test_build123d_sketch_extrude_preserves_four_holes() -> None:
    entities = [
        {"kind": "rectangle", "width": 80.0, "height": 60.0, "operation": "add", "center": [0.0, 0.0]},
    ]
    for x in (-30.0, 30.0):
        for y in (-20.0, 20.0):
            entities.append(
                {"kind": "circle", "radius": 2.0, "operation": "subtract", "center": [x, y]}
            )
    program = _program(
        Feature(
            id="plate_sketch",
            kind="sketch",
            parameters={"plane": "XY", "entities": entities, "constraints": []},
        ),
        Feature(
            id="plate",
            kind="extrude",
            inputs=("plate_sketch",),
            parameters={"distance": 6.0, "operation": "new"},
        ),
        output="plate",
    )
    receipt = Build123dBackend().build_receipt(program)
    expected = 80.0 * 60.0 * 6.0 - 4.0 * math.pi * 2.0**2 * 6.0
    assert receipt.inspection.valid_brep
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((80.0, 60.0, 6.0), abs=1e-7)
    assert receipt.inspection.volume_mm3 == pytest.approx(expected, rel=1e-7)


def test_build123d_revolve_creates_hollow_cylinder() -> None:
    program = _program(
        Feature(
            id="profile",
            kind="sketch",
            parameters={
                "plane": "XY",
                "entities": [
                    {
                        "kind": "rectangle",
                        "width": 10.0,
                        "height": 20.0,
                        "operation": "add",
                        "center": [10.0, 0.0],
                    }
                ],
                "constraints": [],
            },
        ),
        Feature(
            id="revolved",
            kind="revolve",
            inputs=("profile",),
            parameters={"angle_deg": 360.0, "axis": [0.0, 1.0, 0.0], "operation": "new"},
        ),
        output="revolved",
    )
    receipt = Build123dBackend().build_receipt(program)
    expected = math.pi * (15.0**2 - 5.0**2) * 20.0
    assert receipt.inspection.valid_brep
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((30.0, 20.0, 30.0), abs=1e-6)
    assert receipt.inspection.volume_mm3 == pytest.approx(expected, rel=1e-7)


@pytest.mark.parametrize(
    ("kind", "parameters"),
    [
        ("fillet", {"radius": 2.0}),
        ("chamfer", {"distance": 2.0}),
    ],
)
def test_build123d_semantic_edge_operations(kind: str, parameters: dict[str, float]) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        Feature(
            id="finished",
            kind=kind,
            inputs=("body",),
            parameters=parameters,
            selectors=(
                EntitySelector(
                    entity="edge",
                    generated_by="body",
                    predicates=({"kind": "parallel_to", "axis": [0.0, 0.0, 1.0]},),
                    role="vertical_edges",
                    unique=False,
                ),
            ),
        ),
        output="finished",
    )
    receipt = Build123dBackend().build_receipt(program)
    assert receipt.inspection.valid_brep
    assert receipt.inspection.manifold
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((40.0, 30.0, 20.0), abs=1e-7)
    assert receipt.inspection.volume_mm3 < 24000.0


def test_build123d_step_roundtrip_retains_geometry(tmp_path) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [32.0, 24.0, 8.0]}),
        output="body",
    )
    receipt = Build123dBackend().export_verified_step(program, tmp_path / "exact-export")
    assert receipt.step_path == "design.step"
    assert receipt.step_sha256
    assert receipt.roundtrip_inspection is not None
    assert receipt.roundtrip_inspection.valid_brep
    assert receipt.roundtrip_inspection.solid_count == receipt.inspection.solid_count
    assert receipt.roundtrip_inspection.extents_mm == pytest.approx(receipt.inspection.extents_mm, abs=1e-6)
    assert receipt.roundtrip_inspection.volume_mm3 == pytest.approx(receipt.inspection.volume_mm3, rel=1e-8)
    assert (tmp_path / "exact-export" / "design.step").is_file()
    assert (tmp_path / "exact-export" / "build-receipt.json").is_file()


def test_build123d_step_roundtrip_fails_closed_on_geometry_drift(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [32.0, 24.0, 8.0]}),
        output="body",
    )
    backend = Build123dBackend()
    monkeypatch.setattr(backend.bd, "import_step", lambda _: backend.bd.Box(33.0, 24.0, 8.0))
    destination = tmp_path / "drifted-export"
    with pytest.raises(Build123dCompileError, match="changed extent"):
        backend.export_verified_step(program, destination)
    assert not destination.exists()


def test_feature_build_cli_writes_verified_step_bundle(tmp_path, capsys) -> None:
    from core.feature_ir import serialize_feature_ir_json
    from neurocad_cli import build_parser

    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [18.0, 12.0, 4.0]}),
        output="body",
    )
    source = tmp_path / "cli-box.ncad2.json"
    source.write_text(serialize_feature_ir_json(program), encoding="utf-8")
    output = tmp_path / "cli-exact"
    args = build_parser().parse_args(
        ["feature", "build", str(source), "--backend", "build123d", "--output-dir", str(output)]
    )
    assert args.func(args) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["backend"] == "build123d"
    assert payload["inspection"]["valid_brep"] is True
    assert payload["roundtrip_inspection"]["valid_brep"] is True
    assert (output / "design.step").is_file()
    assert (output / "build-receipt.json").is_file()


def test_build123d_named_parameter_edit_changes_exact_geometry() -> None:
    feature = Feature(
        id="body",
        kind="primitive_box",
        parameters={"size": [{"parameter": "width"}, 12.0, 4.0]},
    )
    small = FeatureProgram(
        title="small",
        parameters=(DesignParameter("width", 18.0, lower=10.0, upper=50.0),),
        features=(feature,),
        outputs=("body",),
    )
    large = FeatureProgram(
        title="large",
        parameters=(DesignParameter("width", 27.0, lower=10.0, upper=50.0),),
        features=(feature,),
        outputs=("body",),
    )
    backend = Build123dBackend()
    small_receipt = backend.build_receipt(small)
    large_receipt = backend.build_receipt(large)
    assert small_receipt.inspection.extents_mm == pytest.approx((18.0, 12.0, 4.0), abs=1e-8)
    assert large_receipt.inspection.extents_mm == pytest.approx((27.0, 12.0, 4.0), abs=1e-8)
    assert large_receipt.inspection.volume_mm3 / small_receipt.inspection.volume_mm3 == pytest.approx(1.5)


def _width_requirements(program: FeatureProgram, width_mm: float) -> tuple[RequirementIR, RequirementBindingSet]:
    source = f"Make the box {width_mm:g} mm wide."
    phrase = f"{width_mm:g} mm wide"
    start = source.index(phrase)
    document = RequirementIR(
        source=source,
        requirements=(
            Requirement(
                id="width",
                kind="dimension",
                strength="must",
                target="body.width",
                source_start=start,
                source_end=start + len(phrase),
                source_text=phrase,
                provenance="explicit",
                verification="exact_dimension",
                value=RequirementValue(width_mm, "mm", 0.001),
            ),
        ),
    )
    bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(document),
        feature_ir_sha256=feature_ir_sha256(program),
        bindings=(
            ExactRequirementBinding(
                requirement_id="width",
                feature_ids=("body",),
                verification="exact_dimension",
                probe={"kind": "output_extent", "axis": "x"},
            ),
        ),
    )
    return document, bindings


def test_build123d_verified_export_publishes_requirement_evidence(tmp_path) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        output="body",
    )
    requirements, bindings = _width_requirements(program, 40.0)
    destination = tmp_path / "requirements-pass"
    receipt = Build123dBackend().export_verified_step(
        program,
        destination,
        requirements=requirements,
        binding_set=bindings,
    )
    assert receipt.requirements_satisfied is True
    assert receipt.requirements_path == "requirements.json"
    assert receipt.bindings_path == "requirement-bindings.json"
    assert receipt.requirements_verification_path == "requirements-verification.json"
    assert receipt.requirements_sha256
    assert receipt.bindings_sha256
    assert receipt.requirements_verification_sha256
    assert (destination / "requirements.json").is_file()
    assert (destination / "requirement-bindings.json").is_file()
    assert (destination / "requirements-verification.json").is_file()


def test_build123d_valid_brep_with_wrong_must_dimension_publishes_nothing(tmp_path) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        output="body",
    )
    requirements, bindings = _width_requirements(program, 41.0)
    destination = tmp_path / "requirements-fail"
    with pytest.raises(Build123dCompileError, match="must-level requirement verification failed"):
        Build123dBackend().export_verified_step(
            program,
            destination,
            requirements=requirements,
            binding_set=bindings,
        )
    assert not destination.exists()


def test_build123d_requires_requirement_document_and_bindings_together(tmp_path) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        output="body",
    )
    requirements, _ = _width_requirements(program, 40.0)
    destination = tmp_path / "requirements-incomplete"
    with pytest.raises(Build123dCompileError, match="must be supplied together"):
        Build123dBackend().export_verified_step(
            program,
            destination,
            requirements=requirements,
        )
    assert not destination.exists()


def test_feature_build_cli_enforces_requirement_files_atomically(tmp_path, capsys) -> None:
    from core.feature_ir import serialize_feature_ir_json
    from neurocad_cli import build_parser

    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        output="body",
    )
    requirements, bindings = _width_requirements(program, 40.0)
    program_path = tmp_path / "bound-box.ncad2.json"
    requirements_path = tmp_path / "requirements.json"
    bindings_path = tmp_path / "bindings.json"
    program_path.write_text(serialize_feature_ir_json(program), encoding="utf-8")
    requirements_path.write_text(serialize_requirement_ir_json(requirements), encoding="utf-8")
    bindings_path.write_text(serialize_binding_set_json(bindings), encoding="utf-8")
    destination = tmp_path / "bound-cli"

    args = build_parser().parse_args(
        [
            "feature",
            "build",
            str(program_path),
            "--backend",
            "build123d",
            "--output-dir",
            str(destination),
            "--requirements",
            str(requirements_path),
            "--bindings",
            str(bindings_path),
        ]
    )
    assert args.func(args) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["requirements_satisfied"] is True
    assert (destination / "requirements-verification.json").is_file()



def _revision_wall_panel(
    wall_thickness_mm: float,
    *,
    cutout_center: tuple[float, float] = (-39.0, 10.0),
) -> FeatureProgram:
    inner_width = 80.0 - 2.0 * wall_thickness_mm
    inner_height = 60.0 - 2.0 * wall_thickness_mm
    return FeatureProgram(
        title="C3D bounded wall-thickness revision fixture",
        parameters=(
            DesignParameter(
                "wall_thickness",
                wall_thickness_mm,
                lower=0.25,
                role="edited wall thickness",
            ),
        ),
        features=(
            Feature(
                id="front_profile",
                kind="sketch",
                parameters={
                    "plane": "XY",
                    "entities": [
                        {
                            "kind": "rectangle",
                            "width": 80.0,
                            "height": 60.0,
                            "operation": "add",
                            "center": [0.0, 0.0],
                        },
                        {
                            "kind": "rectangle",
                            "width": inner_width,
                            "height": inner_height,
                            "operation": "subtract",
                            "center": [0.0, 0.0],
                        },
                        {
                            "kind": "circle",
                            "radius": 0.4,
                            "operation": "subtract",
                            "center": [cutout_center[0], cutout_center[1]],
                        },
                    ],
                    "constraints": [],
                },
                role="constant_external_envelope_with_authorized_inner_cavity",
            ),
            Feature(
                id="panel",
                kind="extrude",
                inputs=("front_profile",),
                parameters={
                    "distance": 20.0,
                    "operation": "new",
                },
                role="bounded_enclosure_wall_fixture",
            ),
        ),
        outputs=("panel",),
        metadata={"fixture": "c3d-revision-integrity-v0.1"},
    )


def _panel_requirement_document(wall_thickness_mm: float) -> RequirementIR:
    source = (
        f"Keep width exactly 80 mm and set wall thickness to "
        f"{wall_thickness_mm:g} mm."
    )
    width_text = "80 mm"
    thickness_text = f"{wall_thickness_mm:g} mm"
    width_start = source.index(width_text)
    thickness_start = source.rindex(thickness_text)
    return RequirementIR(
        source=source,
        requirements=(
            Requirement(
                id="width",
                kind="dimension",
                strength="must",
                target="panel.width",
                source_start=width_start,
                source_end=width_start + len(width_text),
                source_text=width_text,
                provenance="explicit",
                verification="exact_dimension",
                value=RequirementValue(80.0, "mm", 1e-6),
            ),
            Requirement(
                id="wall_thickness",
                kind="dimension",
                strength="must",
                target="panel.wall_thickness",
                source_start=thickness_start,
                source_end=thickness_start + len(thickness_text),
                source_text=thickness_text,
                provenance="explicit",
                verification="exact_dimension",
                value=RequirementValue(wall_thickness_mm, "mm", 1e-6),
            ),
        ),
    )


def _panel_requirements(
    program: FeatureProgram,
    wall_thickness_mm: float,
) -> tuple[RequirementIR, RequirementBindingSet]:
    document = _panel_requirement_document(wall_thickness_mm)
    bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(document),
        feature_ir_sha256=feature_ir_sha256(program),
        bindings=(
            ExactRequirementBinding(
                requirement_id="width",
                feature_ids=("panel",),
                verification="exact_dimension",
                probe={"kind": "output_extent", "axis": "x"},
            ),
            ExactRequirementBinding(
                requirement_id="wall_thickness",
                feature_ids=("panel",),
                verification="exact_dimension",
                probe={
                    "kind": "planar_wall_thickness",
                    "axis": "z",
                    "side": "min",
                },
            ),
        ),
    )
    return document, bindings


def _bundle_hashes(path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def test_wall_thickness_edit_preserves_external_boundary_exactly() -> None:
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    evidence = Build123dBackend().compare_planar_revision_boundary(
        baseline,
        candidate,
    )
    assert evidence.external_boundary_equivalent
    assert evidence.external_extents_equivalent
    assert evidence.max_external_extent_delta_mm <= evidence.linear_tolerance_mm
    assert evidence.max_sampled_external_deviation_mm <= evidence.linear_tolerance_mm
    assert evidence.baseline_inspection.extents_mm == pytest.approx(
        (80.0, 60.0, 20.0),
        abs=1e-6,
    )
    assert evidence.candidate_inspection.extents_mm == pytest.approx(
        (80.0, 60.0, 20.0),
        abs=1e-6,
    )
    assert evidence.baseline_wall_thickness_mm == pytest.approx(2.0, abs=1e-6)
    assert evidence.candidate_wall_thickness_mm == pytest.approx(3.0, abs=1e-6)
    assert evidence.candidate_face_area_mm2 > evidence.baseline_face_area_mm2
    assert evidence.passed


def test_wall_thickness_edit_preserves_cutout_geometry_and_position() -> None:
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    evidence = Build123dBackend().compare_planar_revision_boundary(
        baseline,
        candidate,
    )
    assert evidence.cutout_count_baseline == 1
    assert evidence.cutout_count_candidate == 1
    assert evidence.cutouts_equivalent
    assert evidence.max_sampled_cutout_deviation_mm <= evidence.linear_tolerance_mm
    assert evidence.passed


def test_wall_thickness_edit_keeps_single_valid_manifold_solid() -> None:
    evidence = Build123dBackend().compare_planar_revision_boundary(
        _revision_wall_panel(2.0),
        _revision_wall_panel(3.0),
    )
    assert evidence.candidate_inspection.valid_brep
    assert evidence.candidate_inspection.manifold
    assert evidence.candidate_inspection.solid_count == 1
    assert evidence.baseline_self_intersection_free
    assert evidence.candidate_self_intersection_free
    assert evidence.candidate_zero_thickness_free
    assert (
        evidence.candidate_minimum_material_clearance_mm
        > evidence.linear_tolerance_mm
    )


def test_wall_thickness_edit_rechecks_unchanged_must_requirements(tmp_path) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "baseline-accepted"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    candidate_receipt, revision_receipt = backend.export_verified_revision(
        baseline,
        candidate,
        accepted,
        tmp_path / "candidate-accepted",
        baseline_requirements=baseline_requirements,
        baseline_binding_set=baseline_bindings,
        candidate_requirements=candidate_requirements,
        candidate_binding_set=candidate_bindings,
        edited_requirement_ids=("wall_thickness",),
    )

    assert candidate_receipt.requirements_satisfied is True
    assert revision_receipt.unchanged_requirements_guard_passed is True
    assert revision_receipt.baseline_requirements_sha256 == hashlib.sha256(
        (accepted / "requirements.json").read_bytes()
    ).hexdigest()
    assert revision_receipt.baseline_bindings_sha256 == hashlib.sha256(
        (accepted / "requirement-bindings.json").read_bytes()
    ).hexdigest()
    assert revision_receipt.candidate_requirements_sha256 is not None
    assert revision_receipt.candidate_bindings_sha256 is not None
    verification_payload = json.loads(
        (
            tmp_path
            / "candidate-accepted"
            / "requirements-verification.json"
        ).read_text(encoding="utf-8")
    )
    wall_check = next(
        check
        for check in verification_payload["checks"]
        if check["requirement_id"] == "wall_thickness"
    )
    assert wall_check["basis"] == "exact_kernel_planar_wall_thickness"
    assert wall_check["actual"] == pytest.approx(3.0, abs=1e-6)
    assert (tmp_path / "candidate-accepted" / "revision-integrity.json").is_file()


def test_wall_thickness_requirement_uses_geometry_not_parameter_store(
    tmp_path,
) -> None:
    backend = Build123dBackend()
    geometric_two_mm = _revision_wall_panel(2.0)
    lying_program = FeatureProgram(
        title=geometric_two_mm.title,
        parameters=(
            DesignParameter(
                "wall_thickness",
                3.0,
                lower=0.25,
                role="edited wall thickness",
            ),
        ),
        features=geometric_two_mm.features,
        outputs=geometric_two_mm.outputs,
        metadata=dict(geometric_two_mm.metadata),
    )
    requirements, bindings = _panel_requirements(lying_program, 3.0)

    with pytest.raises(
        Build123dCompileError,
        match="must-level requirement verification failed: wall_thickness",
    ):
        backend.export_verified_step(
            lying_program,
            tmp_path / "parameter-store-lie",
            requirements=requirements,
            binding_set=bindings,
        )
    assert not (tmp_path / "parameter-store-lie").exists()


def test_infeasible_40mm_wall_edit_preserves_last_accepted_bundle(tmp_path) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    accepted = tmp_path / "accepted"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )
    before = _bundle_hashes(accepted)

    candidate = _revision_wall_panel(40.0)
    candidate_requirements = _panel_requirement_document(40.0)
    candidate_bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(candidate_requirements),
        # The candidate Feature IR is intentionally invalid and cannot be
        # serialized as accepted geometry. This binding set carries only the
        # pre-edit requirement intent into the fail-closed rejection path.
        feature_ir_sha256=baseline_bindings.feature_ir_sha256,
        bindings=baseline_bindings.bindings,
        metadata=dict(baseline_bindings.metadata),
        version=baseline_bindings.version,
    )
    rejected = tmp_path / "rejected"
    with pytest.raises(
        Build123dCompileError,
        match="rectangle 1 requires positive width and height",
    ):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            rejected,
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )

    assert not rejected.exists()
    assert _bundle_hashes(accepted) == before


def test_infeasible_edit_does_not_relax_unchanged_bindings() -> None:
    baseline = _revision_wall_panel(2.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    rejected_requirements = _panel_requirement_document(40.0)
    rejected_bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(rejected_requirements),
        feature_ir_sha256=baseline_bindings.feature_ir_sha256,
        bindings=baseline_bindings.bindings,
        metadata=dict(baseline_bindings.metadata),
        version=baseline_bindings.version,
    )

    errors = verify_unchanged_must_requirements(
        baseline_requirements,
        baseline_bindings,
        rejected_requirements,
        rejected_bindings,
        edited_requirement_ids=("wall_thickness",),
    )
    assert errors == ()
    assert (
        rejected_bindings.bindings[0].to_dict()
        == baseline_bindings.bindings[0].to_dict()
    )
    assert (
        rejected_bindings.bindings[1].to_dict()
        == baseline_bindings.bindings[1].to_dict()
    )

def test_revision_receipt_binds_baseline_candidate_and_tolerances(tmp_path) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-receipt"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )
    output = tmp_path / "candidate-receipt"

    _candidate_receipt, revision_receipt = backend.export_verified_revision(
        baseline,
        candidate,
        accepted,
        output,
        baseline_requirements=baseline_requirements,
        baseline_binding_set=baseline_bindings,
        candidate_requirements=candidate_requirements,
        candidate_binding_set=candidate_bindings,
        edited_requirement_ids=("wall_thickness",),
    )
    payload = json.loads((output / "revision-integrity.json").read_text(encoding="utf-8"))

    assert payload == revision_receipt.to_dict()
    assert payload["revision_bundle_receipt_version"] == "neurocad-revision-bundle-receipt-v1"
    assert payload["baseline_feature_ir_sha256"] == feature_ir_sha256(baseline)
    assert payload["candidate_feature_ir_sha256"] == feature_ir_sha256(candidate)
    assert payload["evidence"]["linear_tolerance_mm"] == 1e-6
    assert payload["evidence"]["relative_scalar_tolerance"] == 1e-9
    assert payload["evidence"]["absolute_scalar_floor"] == 1e-12
    assert payload["evidence"]["passed"] is True
    assert payload["baseline_step_sha256"] == hashlib.sha256(
        (accepted / "design.step").read_bytes()
    ).hexdigest()
    assert payload["baseline_requirements_verification_sha256"] == hashlib.sha256(
        (accepted / "requirements-verification.json").read_bytes()
    ).hexdigest()
    assert payload["candidate_requirements_verification_sha256"] == hashlib.sha256(
        (output / "requirements-verification.json").read_bytes()
    ).hexdigest()


def test_revision_comparison_rejects_unintended_cutout_motion() -> None:
    evidence = Build123dBackend().compare_planar_revision_boundary(
        _revision_wall_panel(2.0),
        _revision_wall_panel(3.0, cutout_center=(-39.0, 11.0)),
    )
    assert not evidence.cutouts_equivalent
    assert evidence.max_sampled_cutout_deviation_mm > evidence.linear_tolerance_mm
    assert not evidence.passed



def test_revision_rejects_unrelated_or_tampered_baseline_bundle(tmp_path) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-baseline-binding"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    receipt_path = accepted / "build-receipt.json"
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["feature_ir_sha256"] = "0" * 64
    receipt_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Build123dCompileError, match="does not target"):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            tmp_path / "must-not-publish",
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )
    assert not (tmp_path / "must-not-publish").exists()



@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"linear_tolerance_mm": 2.0}, "frozen C3D pilot tolerances"),
        ({"side": "max"}, "frozen to axis='z' and side='min'"),
        (
            {"edited_requirement_ids": ("wall_thickness", "width")},
            "frozen to the wall_thickness requirement only",
        ),
    ],
)
def test_revision_publication_rejects_frozen_contract_widening(
    tmp_path,
    override,
    message,
) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-frozen-contract"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    kwargs = {
        "baseline_requirements": baseline_requirements,
        "baseline_binding_set": baseline_bindings,
        "candidate_requirements": candidate_requirements,
        "candidate_binding_set": candidate_bindings,
        "edited_requirement_ids": ("wall_thickness",),
    }
    kwargs.update(override)

    with pytest.raises(Build123dCompileError, match=message):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            tmp_path / "must-not-publish-widened-contract",
            **kwargs,
        )
    assert not (tmp_path / "must-not-publish-widened-contract").exists()


def test_revision_rejects_baseline_step_geometry_tamper_even_if_receipt_hash_is_updated(
    tmp_path,
) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-step-tamper"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    moved_baseline = _revision_wall_panel(2.0, cutout_center=(-39.0, 11.0))
    moved_shape = next(iter(backend.compile(moved_baseline).values()))
    step_path = accepted / "design.step"
    assert backend.bd.export_step(moved_shape, step_path)

    receipt_path = accepted / "build-receipt.json"
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["step_sha256"] = hashlib.sha256(step_path.read_bytes()).hexdigest()
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        Build123dCompileError,
        match="verified STEP cutout geometry differs",
    ):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            tmp_path / "must-not-publish-step-tamper",
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )
    assert not (tmp_path / "must-not-publish-step-tamper").exists()


def test_revision_rejects_staged_candidate_verification_mutation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-candidate-verification-mutation"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    original_export = backend.export_verified_step

    def mutate_candidate_verification_after_export(*args, **kwargs):
        receipt = original_export(*args, **kwargs)
        candidate_bundle = args[1]
        verification_path = candidate_bundle / "requirements-verification.json"
        verification_path.write_text(
            verification_path.read_text(encoding="utf-8") + " ",
            encoding="utf-8",
        )
        return receipt

    monkeypatch.setattr(
        backend,
        "export_verified_step",
        mutate_candidate_verification_after_export,
    )

    output = tmp_path / "must-not-publish-candidate-verification-mutation"
    with pytest.raises(
        Build123dCompileError,
        match="candidate requirement verification hash does not match",
    ):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            output,
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )
    assert not output.exists()


def test_revision_rejects_candidate_step_export_drift_with_same_extents_and_volume(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-candidate-export-drift"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    moved_candidate = _revision_wall_panel(3.0, cutout_center=(-39.0, 11.0))
    moved_shape = next(iter(backend.compile(moved_candidate).values()))
    original_export_step = backend.bd.export_step

    def export_shifted_cutout(_shape, path):
        return original_export_step(moved_shape, path)

    monkeypatch.setattr(backend.bd, "export_step", export_shifted_cutout)

    output = tmp_path / "must-not-publish-export-drift"
    with pytest.raises(
        Build123dCompileError,
        match="verified STEP cutout geometry differs",
    ):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            output,
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )
    assert not output.exists()


def test_revision_rejects_tampered_baseline_verification_evidence(tmp_path) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-verification-tamper"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    verification_path = accepted / "requirements-verification.json"
    verification_payload = json.loads(verification_path.read_text(encoding="utf-8"))
    verification_payload["satisfied_for_all_must"] = False
    verification_path.write_text(
        json.dumps(verification_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    receipt_path = accepted / "build-receipt.json"
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["requirements_verification_sha256"] = hashlib.sha256(
        verification_path.read_bytes()
    ).hexdigest()
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        Build123dCompileError,
        match="baseline requirement verification does not satisfy every must requirement",
    ):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            tmp_path / "must-not-publish-verification-tamper",
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )
    assert not (tmp_path / "must-not-publish-verification-tamper").exists()


def test_revision_rejects_baseline_verification_mutation_during_evaluation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-verification-race"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    original_export = backend.export_verified_step

    def mutate_baseline_verification_after_candidate(*args, **kwargs):
        receipt = original_export(*args, **kwargs)
        verification_path = accepted / "requirements-verification.json"
        verification_path.write_text(
            verification_path.read_text(encoding="utf-8") + " ",
            encoding="utf-8",
        )
        return receipt

    monkeypatch.setattr(
        backend,
        "export_verified_step",
        mutate_baseline_verification_after_candidate,
    )

    output = tmp_path / "must-not-publish-verification-race"
    with pytest.raises(
        Build123dCompileError,
        match="baseline requirement verification changed during revision evaluation",
    ):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            output,
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )
    assert not output.exists()


def test_revision_rejects_baseline_requirement_mutation_during_evaluation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = Build123dBackend()
    baseline = _revision_wall_panel(2.0)
    candidate = _revision_wall_panel(3.0)
    baseline_requirements, baseline_bindings = _panel_requirements(baseline, 2.0)
    candidate_requirements, candidate_bindings = _panel_requirements(candidate, 3.0)
    accepted = tmp_path / "accepted-race"
    backend.export_verified_step(
        baseline,
        accepted,
        requirements=baseline_requirements,
        binding_set=baseline_bindings,
    )

    original_export = backend.export_verified_step

    def mutate_baseline_after_candidate(*args, **kwargs):
        receipt = original_export(*args, **kwargs)
        requirements_path = accepted / "requirements.json"
        requirements_path.write_text(
            requirements_path.read_text(encoding="utf-8") + " ",
            encoding="utf-8",
        )
        return receipt

    monkeypatch.setattr(backend, "export_verified_step", mutate_baseline_after_candidate)

    output = tmp_path / "must-not-publish-race"
    with pytest.raises(
        Build123dCompileError,
        match="baseline requirements changed during revision evaluation",
    ):
        backend.export_verified_revision(
            baseline,
            candidate,
            accepted,
            output,
            baseline_requirements=baseline_requirements,
            baseline_binding_set=baseline_bindings,
            candidate_requirements=candidate_requirements,
            candidate_binding_set=candidate_bindings,
            edited_requirement_ids=("wall_thickness",),
        )
    assert not output.exists()


def test_revision_comparison_fails_closed_outside_planar_prism_scope() -> None:
    box = _program(
        Feature(
            id="body",
            kind="primitive_box",
            parameters={"size": [80.0, 60.0, 2.0]},
        ),
        output="body",
    )
    with pytest.raises(Build123dCompileError, match="one sketch followed by one extrusion"):
        Build123dBackend().compare_planar_revision_boundary(box, box)
