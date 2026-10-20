from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.fit_revision import (
    apply_fit_revision,
    create_fit_revision_plan,
    parse_fit_revision_plan,
    serialize_fit_revision_plan,
    verify_applied_fit_revision,
    verify_fit_revision_plan,
)
from core.fit_study import create_fit_evidence_bundle, create_fit_study_bundle
from core.project import EnclosureProject, read_project, write_project


def _project(kind: str = "rectangular") -> EnclosureProject:
    cutout = CutoutSpec(
        "port",
        kind,
        "front",
        (0, 0),
        size_mm=(12, 7) if kind == "rectangular" else None,
        diameter_mm=6 if kind == "circular" else None,
    )
    return EnclosureProject(
        "fit-revision-test",
        EnclosureSpec((80, 60, 30), 2, "fdm_standard", LidSpec("none", 0, 0), cutouts=(cutout,)),
    )


def _observations(bundle: Path, outcomes: list[bool]) -> dict[str, object]:
    document = json.loads((bundle / "observations.template.json").read_text(encoding="utf-8"))
    document["passport"] = {
        "printer_id": "printer-1",
        "printer_model": "Example Printer",
        "printer_firmware": "1.0.0",
        "nozzle_diameter_mm": 0.4,
        "material_vendor": "Example Materials",
        "material_product": "PLA",
        "material_lot": "lot-A",
        "slicer": "Example Slicer",
        "slicer_version": "1.2.3",
        "process_profile": "0.2 mm layers",
        "layer_height_mm": 0.2,
        "extrusion_width_mm": 0.45,
        "orientation": "flat XY",
        "mating_part_id": "connector-1",
        "mating_part_reference": "retained measurement record CONNECTOR-2026-10-18",
        "instrument": "caliper-1",
        "instrument_calibration_id": "CAL-2026-10",
        "measurement_resolution_mm": 0.01,
        "environment": "23 C; 45 percent RH",
        "operator_id": "operator-1",
        "measured_at": "2026-10-18T12:00:00+05:30",
        "acceptance_criterion": "connector inserts fully by hand without visible damage",
        "trial_protocol": "test every retained coupon in ascending marker order",
    }
    for row, outcome in zip(document["observations"], outcomes, strict=True):
        row["fit_succeeded"] = outcome
        row["measured_width_mm"] = 10.0
        row["measured_height_mm"] = 5.0
        row["notes"] = "synthetic software fixture; not a physical result"
    return document


def _sealed_inputs(
    tmp_path: Path,
    *,
    kind: str = "rectangular",
    outcomes: list[bool] | None = None,
    adjustments: tuple[float, ...] = (-0.1, 0.2),
) -> tuple[EnclosureProject, Path, Path]:
    project = _project(kind)
    study, evidence = tmp_path / f"{kind}-study", tmp_path / f"{kind}-evidence"
    create_fit_study_bundle(
        project,
        "port",
        study,
        adjustments_mm=adjustments,
        replicates_per_variant=1,
    )
    attachment = tmp_path / f"{kind}-fixture.txt"
    attachment.write_text("synthetic retained test attachment\n", encoding="utf-8")
    create_fit_evidence_bundle(
        study,
        _observations(study, outcomes or [False, True]),
        [attachment],
        evidence,
    )
    return project, study, evidence


@pytest.mark.parametrize("kind", ["rectangular", "circular"])
def test_fit_revision_plan_preserves_nominal_and_compiled_dimension_semantics(
    tmp_path: Path,
    kind: str,
) -> None:
    project, study, evidence = _sealed_inputs(tmp_path, kind=kind)
    plan = create_fit_revision_plan(project, study, evidence)
    assert plan["evidence"]["disposition"] == "BRACKETED_OBSERVED_TRANSITION"
    assert plan["evidence"]["recommended_tested_adjustment_mm"] == 0.2
    assert plan["review"]["automatically_applied"] is False
    assert plan["review"]["held_out_confirmation_required"] is True
    before = plan["revision"]["compiled_aperture_before_mm"]
    after = plan["revision"]["compiled_aperture_after_mm"]
    assert after == pytest.approx([value + 0.2 for value in before])
    if kind == "rectangular":
        assert plan["revision"]["nominal_before_mm"] == {"size_mm": [12.0, 7.0]}
        assert plan["revision"]["nominal_after_mm"] == {"size_mm": [12.2, 7.2]}
    else:
        assert plan["revision"]["nominal_before_mm"] == {"diameter_mm": 6.0}
        assert plan["revision"]["nominal_after_mm"] == {"diameter_mm": 6.2}
        assert before[0] != 6.0  # compiled profile compensation remains explicit

    encoded = serialize_fit_revision_plan(plan)
    parsed = parse_fit_revision_plan(encoded)
    assert parsed == plan
    assert verify_fit_revision_plan(project, study, evidence, parsed)["valid"] is True


def test_fit_revision_apply_is_auditable_exact_and_single_use(tmp_path: Path) -> None:
    project, study, evidence = _sealed_inputs(tmp_path)
    plan = create_fit_revision_plan(project, study, evidence)
    revised = apply_fit_revision(project, study, evidence, plan)
    assert revised.revision == project.revision + 1
    assert revised.changes[-1].field == "cutouts"
    assert plan["source"]["fit_report_sha256"] in revised.changes[-1].reason
    verified = verify_applied_fit_revision(project, revised, study, evidence, plan)
    assert verified["valid"] is True
    assert verified["held_out_confirmation_required"] is True
    assert verified["physical_fit_certified"] is False

    with pytest.raises(ValueError, match="expected project revision"):
        apply_fit_revision(revised, study, evidence, plan)


def test_fit_revision_rejects_unbracketed_stale_and_tampered_inputs(tmp_path: Path) -> None:
    unbracketed_project, unbracketed_study, unbracketed_evidence = _sealed_inputs(
        tmp_path / "unbracketed",
        outcomes=[True, True],
    )
    with pytest.raises(ValueError, match="bracketed observed transition"):
        create_fit_revision_plan(unbracketed_project, unbracketed_study, unbracketed_evidence)

    zero_project, zero_study, zero_evidence = _sealed_inputs(
        tmp_path / "zero",
        outcomes=[False, True],
        adjustments=(-0.1, 0),
    )
    with pytest.raises(ValueError, match="zero adjustment"):
        create_fit_revision_plan(zero_project, zero_study, zero_evidence)

    project, study, evidence = _sealed_inputs(tmp_path / "bracketed")
    plan = create_fit_revision_plan(project, study, evidence)
    tampered = json.loads(json.dumps(plan))
    tampered["revision"]["nominal_after_mm"]["size_mm"][0] = 99
    with pytest.raises(ValueError, match="does not recompute"):
        verify_fit_revision_plan(project, study, evidence, tampered)

    stale = EnclosureProject(
        "other-project",
        project.spec,
    )
    with pytest.raises(ValueError, match="expected project revision"):
        create_fit_revision_plan(stale, study, evidence)


def test_fit_revision_cli_requires_review_confirmation_and_verifies_output(tmp_path: Path) -> None:
    project, study, evidence = _sealed_inputs(tmp_path)
    project_path, plan_path, revised_path = (
        tmp_path / "project.json",
        tmp_path / "plan.json",
        tmp_path / "revised.json",
    )
    write_project(project_path, project)
    source_before = project_path.read_bytes()
    base = [sys.executable, "-m", "neurocad_cli", "enclosure"]
    contained = subprocess.run(
        [
            *base,
            "fit-revision-plan",
            str(project_path),
            str(study),
            str(evidence),
            "-o",
            str(evidence / "unsafe-plan.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert contained.returncode != 0
    assert not (evidence / "unsafe-plan.json").exists()
    planned = subprocess.run(
        [
            *base,
            "fit-revision-plan",
            str(project_path),
            str(study),
            str(evidence),
            "-o",
            str(plan_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert planned.returncode == 0, planned.stderr
    plan_before = plan_path.read_bytes()
    refused_overwrite = subprocess.run(
        [
            *base,
            "fit-revision-plan",
            str(project_path),
            str(study),
            str(evidence),
            "-o",
            str(plan_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert refused_overwrite.returncode != 0
    assert plan_path.read_bytes() == plan_before

    unconfirmed = subprocess.run(
        [
            *base,
            "fit-revision-apply",
            str(project_path),
            str(study),
            str(evidence),
            str(plan_path),
            "-o",
            str(revised_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert unconfirmed.returncode != 0
    assert not revised_path.exists()

    applied = subprocess.run(
        [
            *base,
            "fit-revision-apply",
            str(project_path),
            str(study),
            str(evidence),
            str(plan_path),
            "-o",
            str(revised_path),
            "--confirm",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert applied.returncode == 0, applied.stderr
    assert read_project(revised_path).revision == 2
    assert project_path.read_bytes() == source_before

    verified = subprocess.run(
        [
            *base,
            "fit-revision-verify",
            str(project_path),
            str(revised_path),
            str(study),
            str(evidence),
            str(plan_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["valid"] is True
