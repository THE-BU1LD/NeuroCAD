from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.fit_study import (
    create_fit_evidence_bundle,
    create_fit_study_bundle,
    evaluate_fit_study,
    verify_fit_evidence_bundle,
    verify_fit_study_bundle,
    verify_fit_study_report,
)
from core.ir_parser import parse_ir_json
from core.project import EnclosureProject, write_project


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
        "fit-study-test",
        EnclosureSpec((80, 60, 30), 2, "fdm_standard", LidSpec("none", 0, 0), cutouts=(cutout,)),
    )


def _completed_observations(bundle: Path, outcomes: list[bool]) -> dict[str, object]:
    template = json.loads((bundle / "observations.template.json").read_text(encoding="utf-8"))
    template["passport"] = {
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
        "mating_part_id": "usb-plug-1",
        "mating_part_reference": "retained measurement record USB-2026-10-18",
        "instrument": "caliper-1",
        "instrument_calibration_id": "CAL-2026-10",
        "measurement_resolution_mm": 0.01,
        "environment": "23 C; 45 percent RH",
        "operator_id": "operator-1",
        "measured_at": "2026-10-18T12:00:00+05:30",
        "acceptance_criterion": "connector inserts fully by hand without visible damage",
        "trial_protocol": "test each retained coupon once in ascending marker order and clean the mating part",
    }
    for row, outcome in zip(template["observations"], outcomes, strict=True):
        row["fit_succeeded"] = outcome
        row["measured_width_mm"] = 10.0
        row["measured_height_mm"] = 5.0
        row["notes"] = "retained observation"
    return template


@pytest.mark.parametrize("kind", ["rectangular", "circular"])
def test_fit_study_generates_bound_canonical_ladder(tmp_path: Path, kind: str) -> None:
    output = tmp_path / f"{kind}-study"
    receipt = create_fit_study_bundle(
        _project(kind),
        output_dir=output,
        cutout_id="port",
        adjustments_mm=(-0.2, 0, 0.3),
        replicates_per_variant=1,
    )
    assert receipt["physical_fit_claimed"] is False
    verified = verify_fit_study_bundle(output, expected_project=_project(kind))
    assert verified["valid"] is True
    assert verified["variant_count"] == 3

    study = json.loads((output / "study.json").read_text(encoding="utf-8"))
    assert [item["aperture_adjustment_mm"] for item in study["variants"]] == [-0.2, 0.0, 0.3]
    programs = [parse_ir_json((output / item["artifact"]).read_text(encoding="utf-8")) for item in study["variants"]]
    generated = [program.metadata["aperture_size_mm"][0] for program in programs]
    assert generated[1] - generated[0] == pytest.approx(0.2)
    assert generated[2] - generated[1] == pytest.approx(0.3)
    assert all(program.metadata["source_project_sha256"] == verified["source_project_sha256"] for program in programs)
    assert [program.metadata["physical_marker"]["code"] for program in programs] == [1, 2, 3]
    assert all((output / f"variant-{index:02d}.scad").is_file() for index in range(1, 4))


def test_fit_study_rejects_invalid_ladders_and_stale_project(tmp_path: Path) -> None:
    for index, values in enumerate(((0,), (0, 0), (True, 0.2), (-5.1, 0))):
        with pytest.raises((TypeError, ValueError)):
            create_fit_study_bundle(
                _project(), "port", tmp_path / f"invalid-{index}", adjustments_mm=values, replicates_per_variant=1
            )
    output = tmp_path / "valid"
    create_fit_study_bundle(_project(), "port", output, adjustments_mm=(-0.1, 0.1), replicates_per_variant=1)
    with pytest.raises(ValueError, match="expected project revision"):
        verify_fit_study_bundle(output, expected_project=replace(_project(), project_id="different-project"))


def test_fit_study_verification_rejects_tampering(tmp_path: Path) -> None:
    output = tmp_path / "study"
    create_fit_study_bundle(_project(), "port", output, adjustments_mm=(-0.1, 0.1), replicates_per_variant=1)
    linked = tmp_path / "study-link"
    linked.symlink_to(output, target_is_directory=True)
    with pytest.raises(ValueError, match="must not be a symbolic link"):
        verify_fit_study_bundle(linked)
    artifact = output / "variant-01.ncad.json"
    artifact.write_text(artifact.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_fit_study_bundle(output)


def test_fit_study_evaluation_reports_observed_transition(tmp_path: Path) -> None:
    output = tmp_path / "study"
    create_fit_study_bundle(
        _project(), "port", output, adjustments_mm=(-0.2, 0, 0.2, 0.4), replicates_per_variant=1
    )
    report = evaluate_fit_study(output, _completed_observations(output, [False, False, True, True]))
    assert report["disposition"] == "BRACKETED_OBSERVED_TRANSITION"
    assert report["observed_failure_edge_mm"] == 0.0
    assert report["observed_success_edge_mm"] == 0.2
    assert report["recommended_tested_adjustment_mm"] == 0.2
    assert report["variant_results"][2]["success_rate"] == 1.0
    assert report["variant_results"][2]["success_rate_wilson_95"][0] < 1.0
    assert report["physical_fit_certified"] is False
    assert verify_fit_study_report(output, report)["valid"] is True
    altered = {**report, "recommended_tested_adjustment_mm": 0.4}
    with pytest.raises(ValueError, match="does not recompute"):
        verify_fit_study_report(output, altered)


def test_fit_study_evaluation_preserves_non_monotone_and_rejects_bad_sets(tmp_path: Path) -> None:
    output = tmp_path / "study"
    create_fit_study_bundle(_project(), "port", output, adjustments_mm=(-0.2, 0, 0.2), replicates_per_variant=1)
    document = _completed_observations(output, [False, True, False])
    report = evaluate_fit_study(output, document)
    assert report["disposition"] == "NON_MONOTONE_INCONSISTENT"
    assert report["recommended_tested_adjustment_mm"] is None
    assert report["non_monotone_violations"] == [{"smaller_success": "variant-02", "larger_failure": "variant-03"}]

    incomplete = _completed_observations(output, [False, True, True])
    incomplete["observations"].pop()
    with pytest.raises(ValueError, match="complete fit-study observations"):
        evaluate_fit_study(output, incomplete)
    duplicate = _completed_observations(output, [False, True, True])
    duplicate["observations"][1]["variant_id"] = "variant-01"
    with pytest.raises(ValueError, match="duplicate fit-study observation"):
        evaluate_fit_study(output, duplicate)
    stale = _completed_observations(output, [False, True, True])
    stale["study_binding_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="not bound"):
        evaluate_fit_study(output, stale)

    placeholder = _completed_observations(output, [False, True, True])
    placeholder["passport"]["material_lot"] = "REQUIRED"
    with pytest.raises(ValueError, match="blank-template placeholder"):
        evaluate_fit_study(output, placeholder)
    timestamp_without_zone = _completed_observations(output, [False, True, True])
    timestamp_without_zone["passport"]["measured_at"] = "2026-10-18T12:00:00"
    with pytest.raises(ValueError, match="explicit UTC offset"):
        evaluate_fit_study(output, timestamp_without_zone)


def test_fit_study_replicates_are_predeclared_and_conservatively_aggregated(tmp_path: Path) -> None:
    output = tmp_path / "replicated-study"
    create_fit_study_bundle(
        _project(), output_dir=output, cutout_id="port", adjustments_mm=(-0.1, 0.1), replicates_per_variant=3
    )
    observations = _completed_observations(output, [True, True, False, True, True, True])
    report = evaluate_fit_study(output, observations)
    assert report["variant_results"][0]["attempts"] == 3
    assert report["variant_results"][0]["successes"] == 2
    assert report["variant_results"][0]["fit_succeeded"] is False
    assert report["variant_results"][1]["fit_succeeded"] is True
    assert report["disposition"] == "BRACKETED_OBSERVED_TRANSITION"
    assert report["recommended_tested_adjustment_mm"] == 0.1


def test_fit_evidence_bundle_binds_attachments_and_recomputes_report(tmp_path: Path) -> None:
    study, evidence = tmp_path / "study", tmp_path / "sealed-evidence"
    create_fit_study_bundle(
        _project(), "port", study, adjustments_mm=(-0.1, 0.1), replicates_per_variant=1
    )
    photo = tmp_path / "coupon-photo.jpg"
    photo.write_bytes(b"retained-test-photo-bytes")
    with pytest.raises(ValueError, match="must not be created inside"):
        create_fit_evidence_bundle(
            study, _completed_observations(study, [False, True]), [photo], study / "sealed"
        )
    assert verify_fit_study_bundle(study)["valid"] is True
    with pytest.raises(ValueError, match="filenames must be unique"):
        create_fit_evidence_bundle(
            study, _completed_observations(study, [False, True]), [photo, photo], tmp_path / "duplicate"
        )
    receipt = create_fit_evidence_bundle(
        study, _completed_observations(study, [False, True]), [photo], evidence
    )
    assert receipt["evidence_authenticity_verified"] is False
    verified = verify_fit_evidence_bundle(study, evidence)
    assert verified["valid"] is True
    assert verified["evidence_file_count"] == 1
    retained = evidence / "evidence-01.jpg"
    retained.write_bytes(retained.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="hash or size mismatch"):
        verify_fit_evidence_bundle(study, evidence)


def test_fit_study_cli_end_to_end_and_collision_refusal(tmp_path: Path) -> None:
    project_path, output = tmp_path / "project.json", tmp_path / "study"
    write_project(project_path, _project())
    command = [
        sys.executable,
        "-m",
        "neurocad_cli",
        "enclosure",
        "fit-study",
        str(project_path),
        "--cutout",
        "port",
        "--adjustment=-0.2",
        "--adjustment=0",
        "--adjustment=0.2",
        "--replicates=1",
        "--output-dir",
        str(output),
    ]
    created = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    assert created.returncode == 0, created.stderr
    before = (output / "manifest.json").read_bytes()
    refused = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    assert refused.returncode != 0
    assert (output / "manifest.json").read_bytes() == before

    verified = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "enclosure", "fit-study-verify", str(output), "--project", str(project_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["variant_count"] == 3

    observations_path, report_path = tmp_path / "observations.json", tmp_path / "report.json"
    observations_path.write_text(json.dumps(_completed_observations(output, [False, True, True])), encoding="utf-8")
    evaluated = subprocess.run(
        [
            sys.executable,
            "-m",
            "neurocad_cli",
            "enclosure",
            "fit-study-evaluate",
            str(output),
            str(observations_path),
            "-o",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert evaluated.returncode == 0, evaluated.stderr
    assert json.loads(report_path.read_text(encoding="utf-8"))["disposition"] == "BRACKETED_OBSERVED_TRANSITION"
    report_verified = subprocess.run(
        [
            sys.executable,
            "-m",
            "neurocad_cli",
            "enclosure",
            "fit-study-report-verify",
            str(output),
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert report_verified.returncode == 0, report_verified.stderr
    assert json.loads(report_verified.stdout)["valid"] is True

    attachment, sealed = tmp_path / "photo.png", tmp_path / "sealed"
    attachment.write_bytes(b"retained-png-fixture")
    sealed_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "neurocad_cli",
            "enclosure",
            "fit-study-seal",
            str(output),
            str(observations_path),
            "--evidence",
            str(attachment),
            "--output-dir",
            str(sealed),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert sealed_result.returncode == 0, sealed_result.stderr
    sealed_verified = subprocess.run(
        [
            sys.executable,
            "-m",
            "neurocad_cli",
            "enclosure",
            "fit-study-seal-verify",
            str(output),
            str(sealed),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert sealed_verified.returncode == 0, sealed_verified.stderr
    assert json.loads(sealed_verified.stdout)["evidence_file_count"] == 1
