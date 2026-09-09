from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROMPT = (
    "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
    "friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; "
    "rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C"
)


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "neurocad_cli", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _calibration_dataset() -> dict[str, object]:
    axes = []
    for axis, factor in (("x", 0.98), ("y", 1.02), ("z", 0.995)):
        for index, nominal in enumerate((20.0, 40.0, 80.0), start=1):
            axes.append(
                {
                    "observation_id": f"axis-{axis}-{index}",
                    "axis": axis,
                    "nominal_mm": nominal,
                    "measured_mm": nominal / factor,
                    "run_id": f"run-{(index % 2) + 1}",
                }
            )
    return {
        "profile_id": "mk4-pla-standard",
        "printer": "Prusa MK4",
        "material": "PLA lot A",
        "process": "0.20 mm structural profile",
        "nozzle_diameter_mm": 0.4,
        "measurement_resolution_mm": 0.01,
        "axis_observations": axes,
        "hole_observations": [
            {
                "observation_id": "hole-1",
                "orientation": "vertical",
                "nominal_diameter_mm": 3,
                "measured_diameter_mm": 2.8,
                "run_id": "run-1",
            },
            {
                "observation_id": "hole-2",
                "orientation": "vertical",
                "nominal_diameter_mm": 5,
                "measured_diameter_mm": 4.8,
                "run_id": "run-2",
            },
            {
                "observation_id": "hole-3",
                "orientation": "horizontal",
                "nominal_diameter_mm": 8,
                "measured_diameter_mm": 7.8,
                "run_id": "run-1",
            },
        ],
        "clearance_observations": [
            {"observation_id": "fit-1", "clearance_mm": 0.1, "fit_succeeded": False, "run_id": "run-1"},
            {"observation_id": "fit-2", "clearance_mm": 0.2, "fit_succeeded": False, "run_id": "run-2"},
            {"observation_id": "fit-3", "clearance_mm": 0.3, "fit_succeeded": True, "run_id": "run-1"},
            {"observation_id": "fit-4", "clearance_mm": 0.4, "fit_succeeded": True, "run_id": "run-2"},
        ],
    }


def test_cli_interpret_edit_preflight_and_build_project_bundle(tmp_path: Path) -> None:
    interpretation = tmp_path / "interpretation.json"
    project = tmp_path / "project-r1.ncad.json"
    interpreted = _run(
        "enclosure",
        "interpret",
        PROMPT,
        "--project-id",
        "controller",
        "--output",
        str(interpretation),
        "--project-output",
        str(project),
    )
    assert interpreted.returncode == 0, interpreted.stderr
    assert json.loads(interpretation.read_text(encoding="utf-8"))["ready"] is True

    revised = tmp_path / "project-r2.ncad.json"
    edited = _run(
        "enclosure",
        "edit",
        str(project),
        "--instruction",
        "set wall thickness to 2.4 mm",
        "--output",
        str(revised),
    )
    assert edited.returncode == 0, edited.stderr
    assert json.loads(revised.read_text(encoding="utf-8"))["revision"] == 2

    preflight = _run("enclosure", "preflight", str(revised))
    assert preflight.returncode == 0, preflight.stderr
    assert json.loads(preflight.stdout)["valid"] is True

    bundle = tmp_path / "bundle-r2"
    built = _run("enclosure", "build", str(revised), "--output-dir", str(bundle))
    assert built.returncode == 0, built.stderr
    build_manifest = json.loads(built.stdout)
    assert build_manifest["schema_version"] == "neurocad-bundle-v1"
    assert build_manifest["generator"] == {"fn": 64}
    assert (bundle / "manifest.json").is_file()

    verified = _run("enclosure", "verify", str(bundle))
    assert verified.returncode == 0, verified.stderr
    verification = json.loads(verified.stdout)
    assert verification["valid"] is True
    assert verification["project_id"] == "controller"
    assert verification["checks"]["openscad_matches_source"] is True
    assert verification["checks"]["mesh_verification"] is None

    extra = bundle / "untracked.txt"
    extra.write_text("not in manifest\n", encoding="utf-8")
    rejected_extra = _run("enclosure", "verify", str(bundle))
    assert rejected_extra.returncode == 2
    assert "directory inventory mismatch" in rejected_extra.stderr
    extra.unlink()

    (bundle / "body.scad").write_text("tampered\n", encoding="utf-8")
    rejected = _run("enclosure", "verify", str(bundle))
    assert rejected.returncode == 2
    assert "hash or size mismatch" in rejected.stderr


def test_cli_fails_closed_on_unknown_language_missing_edit_values_and_path_collisions(tmp_path: Path) -> None:
    missing = tmp_path / "missing-project.json"
    rejected = _run("enclosure", "interpret", PROMPT + "; add wings", "--project-output", str(missing))
    assert rejected.returncode == 2
    assert not missing.exists()

    project = tmp_path / "project.ncad.json"
    created = _run("enclosure", "interpret", PROMPT, "--project-output", str(project))
    assert created.returncode == 0, created.stderr
    invalid_edit = _run(
        "enclosure",
        "edit",
        str(project),
        "--field",
        "wall_mm",
        "--reason",
        "missing value",
        "--output",
        str(tmp_path / "bad.json"),
    )
    assert invalid_edit.returncode == 2
    assert "--value is required" in invalid_edit.stderr

    collision = _run(
        "enclosure",
        "interpret",
        PROMPT,
        "--output",
        str(missing),
        "--project-output",
        str(missing),
    )
    assert collision.returncode == 2
    assert not missing.exists()


def test_cli_lists_apps_exports_bundle_and_creates_truthful_handoff(tmp_path: Path) -> None:
    listed = _run("integrations", "list", "OpenSCAD", "Fusion 360", "Prusa Slicer")
    assert listed.returncode == 0, listed.stderr
    adapters = json.loads(listed.stdout)
    assert [item["id"] for item in adapters["applications"]] == ["openscad", "fusion", "prusaslicer"]
    assert adapters["external_operation_performed"] is False

    project = tmp_path / "project.ncad.json"
    created = _run("enclosure", "interpret", PROMPT, "--project-output", str(project))
    assert created.returncode == 0, created.stderr
    exchange = tmp_path / "exchange"
    neutral = tmp_path / "neutral.json"
    exported = _run(
        "integrations",
        "export",
        str(project),
        "--output-dir",
        str(exchange),
        "--manifest",
        str(neutral),
        "--application",
        "openscad",
        "--application",
        "fusion",
    )
    assert exported.returncode == 0, exported.stderr
    assert json.loads(exported.stdout)["capability"]["state"] == "native"
    assert json.loads(neutral.read_text(encoding="utf-8"))["external_operation_performed"] is False

    handoff = tmp_path / "openscad-handoff.json"
    handed_off = _run("integrations", "handoff", str(exchange), "openscad", "-o", str(handoff))
    assert handed_off.returncode == 0, handed_off.stderr
    receipt = json.loads(handoff.read_text(encoding="utf-8"))
    assert receipt["handoff"]["ready"] is True
    assert receipt["external_operation_executed"] is False

    verified = _run("integrations", "verify", str(exchange))
    assert verified.returncode == 0, verified.stderr
    verification = json.loads(verified.stdout)
    assert verification["valid"] is True
    assert verification["bundle"]["part_count"] == 2
    assert verification["bundle"]["compiled_meshes"] is False

    refused = _run("integrations", "handoff", str(exchange), "openscad", "-o", str(handoff))
    assert refused.returncode == 2
    assert "already exists" in refused.stderr


def test_cli_kicad_contract_requires_receipt_bound_to_source_board(tmp_path: Path) -> None:
    board = tmp_path / "controller.kicad_pcb"
    board.write_text("(kicad_pcb (version 20250101))\n", encoding="utf-8")
    request = tmp_path / "request.json"
    requested = _run("integrations", "kicad-request", str(board), "-o", str(request))
    assert requested.returncode == 0, requested.stderr
    request_payload = json.loads(request.read_text(encoding="utf-8"))
    assert request_payload["operation_executed"] is False

    receipt = {
        "contract_version": "neurocad-kicad-handoff-v1",
        "units": "mm",
        "source": {
            "name": board.name,
            "sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
            "kicad_version": "9.0.0",
        },
        "extraction": {
            "method": "ipc_api",
            "complete": True,
            "complete_fields": [
                "board_outline",
                "board_thickness",
                "mounting_holes",
                "connectors",
                "max_component_height",
            ],
            "warnings": [],
            "unsupported_items": [],
        },
        "board": {
            "outline": {"kind": "rectangle", "width_mm": 50, "height_mm": 30},
            "thickness_mm": 1.6,
            "origin": "board_center",
            "mounting_holes": [
                {"id": "H1", "center_xy_mm": [-20, -10], "diameter_mm": 3},
                {"id": "H2", "center_xy_mm": [20, 10], "diameter_mm": 3},
            ],
            "connectors": [],
            "max_component_height_mm": 10,
        },
    }
    draft = tmp_path / "draft.json"
    draft.write_text(
        json.dumps(
            {
                "draft_version": "neurocad-kicad-extraction-draft-v1",
                "units": receipt["units"],
                "source": {"kicad_version": receipt["source"]["kicad_version"]},
                "extraction": receipt["extraction"],
                "board": receipt["board"],
            }
        ),
        encoding="utf-8",
    )
    completed = tmp_path / "completed.json"
    bound = _run(
        "integrations",
        "kicad-bind",
        str(draft),
        "--source-board",
        str(board),
        "-o",
        str(completed),
    )
    assert bound.returncode == 0, bound.stderr
    receipt = json.loads(completed.read_text(encoding="utf-8"))
    inspected = _run(
        "integrations",
        "kicad-inspect",
        str(completed),
        "--source-board",
        str(board),
    )
    assert inspected.returncode == 0, inspected.stderr
    payload = json.loads(inspected.stdout)
    assert payload["source_hash_verified"] is True
    assert payload["pcb_spec"]["mounting_holes_xy_mm"] == [[-20.0, -10.0], [20.0, 10.0]]

    project = tmp_path / "project-r1.ncad.json"
    created = _run("enclosure", "interpret", PROMPT, "--project-output", str(project))
    assert created.returncode == 0, created.stderr
    revised = tmp_path / "project-r2.ncad.json"
    applied = _run(
        "integrations",
        "kicad-apply",
        str(project),
        str(completed),
        "--source-board",
        str(board),
        "-o",
        str(revised),
    )
    assert applied.returncode == 0, applied.stderr
    applied_payload = json.loads(applied.stdout)
    assert applied_payload["revision"] == 2
    assert applied_payload["source"]["hash_verified"] is True
    assert applied_payload["automatically_created_cutouts"] is False
    assert applied_payload["automatically_created_standoffs"] is False
    revised_payload = json.loads(revised.read_text(encoding="utf-8"))
    assert revised_payload["spec"]["pcb"]["size_mm"] == [50.0, 30.0, 1.6]
    assert receipt["source"]["sha256"] in revised_payload["changes"][0]["reason"]

    board.write_text("tampered\n", encoding="utf-8")
    rejected_output = tmp_path / "rejected.json"
    rejected = _run(
        "integrations",
        "kicad-apply",
        str(project),
        str(completed),
        "--source-board",
        str(board),
        "-o",
        str(rejected_output),
    )
    assert rejected.returncode == 2
    assert "hash does not match" in rejected.stderr
    assert not rejected_output.exists()


def test_cli_extracts_a_bounded_kicad_file_into_a_hash_bound_receipt(tmp_path: Path) -> None:
    board = tmp_path / "sensor.kicad_pcb"
    board.write_text(
        '''(kicad_pcb
  (version 20250101)
  (generator pcbnew)
  (general (thickness 1.6))
  (gr_rect (start 10 20) (end 60 50) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts"))
)\n''',
        encoding="utf-8",
    )
    review = tmp_path / "mechanical-review.json"
    review.write_text(
        json.dumps(
            {
                "review_version": "neurocad-kicad-mechanical-review-v1",
                "connector_inventory_complete": True,
                "component_height_measured": True,
                "max_component_height_mm": 7.5,
                "connectors": [],
            }
        ),
        encoding="utf-8",
    )
    receipt = tmp_path / "bounded-receipt.json"
    extracted = _run(
        "integrations",
        "kicad-extract",
        str(board),
        "--review",
        str(review),
        "-o",
        str(receipt),
    )
    assert extracted.returncode == 0, extracted.stderr
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["extraction"]["method"] == "bounded_file_parser"
    assert payload["board"]["outline"] == {"height_mm": 30.0, "kind": "rectangle", "width_mm": 50.0}

    inspected = _run("integrations", "kicad-inspect", str(receipt), "--source-board", str(board))
    assert inspected.returncode == 0, inspected.stderr
    assert json.loads(inspected.stdout)["source_hash_verified"] is True

    refused = _run(
        "integrations",
        "kicad-extract",
        str(board),
        "--review",
        str(review),
        "-o",
        str(receipt),
    )
    assert refused.returncode == 2
    assert "already exists" in refused.stderr


def test_cli_fits_plans_and_applies_evidence_bounded_calibration(tmp_path: Path) -> None:
    dataset = tmp_path / "coupon-observations.json"
    dataset.write_text(json.dumps(_calibration_dataset()), encoding="utf-8")
    profile = tmp_path / "calibration-profile.json"
    fitted = _run("calibration", "fit", str(dataset), "-o", str(profile))
    assert fitted.returncode == 0, fitted.stderr

    inspected = _run("calibration", "inspect", str(profile))
    assert inspected.returncode == 0, inspected.stderr
    fitted_payload = json.loads(inspected.stdout)
    assert fitted_payload["method_version"] == "robust-coupon-fit-v2"
    assert fitted_payload["recommendations"]["clearance"]["recommended_clearance_mm"] == 0.3

    project = tmp_path / "project-r1.ncad.json"
    created = _run(
        "enclosure",
        "interpret",
        PROMPT.replace("clearance 0.3", "clearance 0.1"),
        "--project-output",
        str(project),
    )
    assert created.returncode == 0, created.stderr
    plan = _run("calibration", "plan", str(project), str(profile))
    assert plan.returncode == 0, plan.stderr
    assert json.loads(plan.stdout)["automatically_applied"] is False

    revised = tmp_path / "project-r2.ncad.json"
    applied = _run("calibration", "apply-clearance", str(project), str(profile), "-o", str(revised))
    assert applied.returncode == 0, applied.stderr
    assert json.loads(revised.read_text(encoding="utf-8"))["revision"] == 2
