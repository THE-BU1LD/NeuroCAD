from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec, PCBSpec, StandoffSpec
from core.interface_contract import (
    CHANGE_IMPACT_VERSION,
    INTERFACE_CONTRACT_VERSION,
    create_interface_contract,
    evaluate_project_change,
    parse_interface_document,
    require_protected_interfaces,
    serialize_interface_document,
    verify_change_impact_report,
    verify_interface_contract,
)
from core.project import EnclosureProject, enclosure_spec_to_dict, update_project, write_project


def _project() -> EnclosureProject:
    return EnclosureProject(
        "protected-controller",
        EnclosureSpec(
            outer_size_mm=(100, 80, 40),
            wall_mm=2,
            floor_mm=2,
            corner_radius_mm=3,
            profile="fdm_standard",
            lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
            cutouts=(
                CutoutSpec("usb", "rectangular", "front", (0, 0), size_mm=(12, 7), purpose="USB-C"),
                CutoutSpec("power", "circular", "rear", (12, 0), diameter_mm=8, purpose="barrel jack"),
            ),
            standoffs=(
                StandoffSpec("board_a", (-20, -12), 6, 7.5, 2.5, "M3"),
                StandoffSpec("board_b", (20, 12), 6, 7.5, 2.5, "M3"),
            ),
            pcb=PCBSpec(
                (60, 40, 10),
                mounting_holes_xy_mm=((-20, -12), (20, 12)),
            ),
        ),
    )


def _contract(project: EnclosureProject, *, tolerance: float = 0.0) -> dict[str, object]:
    return create_interface_contract(
        project,
        contract_id="controller-v1",
        cutout_ids=("usb",),
        standoff_ids=("board_a", "board_b"),
        lock_pcb_mounting=True,
        lock_lid_interface=True,
        tolerance_mm=tolerance,
    )


def test_contract_is_deterministic_source_bound_and_recomputable() -> None:
    project = _project()
    contract = _contract(project)
    assert contract["schema_version"] == INTERFACE_CONTRACT_VERSION
    assert len(contract["locks"]) == 5
    assert contract["physical_compatibility_certified"] is False
    encoded = serialize_interface_document(contract)
    assert parse_interface_document(encoded, expected_version=INTERFACE_CONTRACT_VERSION) == contract
    verified = verify_interface_contract(project, contract)
    assert verified["valid"] is True
    assert verified["lock_count"] == 5

    tampered = deepcopy(contract)
    tampered["locks"][0]["snapshot"]["center_uv_mm"][0] = 5
    with pytest.raises(ValueError, match="does not recompute"):
        verify_interface_contract(project, tampered)
    stale = update_project(project, "title", "renamed", reason="rename")
    with pytest.raises(ValueError, match="does not recompute"):
        verify_interface_contract(stale, contract)


def test_unlocked_edit_passes_and_reports_precise_invalidations() -> None:
    project = _project()
    contract = _contract(project)
    candidate = update_project(project, "title", "field controller", reason="clearer title")
    report = require_protected_interfaces(project, candidate, contract)
    assert report["schema_version"] == CHANGE_IMPACT_VERSION
    assert report["decision"] == "ACCEPTED"
    assert report["lineage"]["valid"] is True
    assert report["regeneration_required"] is False
    assert report["impacts"] == [
        {
            "field": "title",
            "affected_scopes": ["project_metadata"],
            "invalidated_evidence": [],
            "reason": "project title changed without geometry",
        }
    ]
    assert report["interface_contract"]["valid"] is True
    assert verify_change_impact_report(project, candidate, report, contract=contract)["valid"] is True


def test_locked_connector_mount_and_lid_changes_fail_closed() -> None:
    project = _project()
    contract = _contract(project)
    spec = enclosure_spec_to_dict(project.spec)

    cutouts = deepcopy(spec["cutouts"])
    cutouts[0]["center_uv_mm"] = [1, 0]
    moved_cutout = update_project(project, "cutouts", cutouts, reason="move connector")
    cutout_report = evaluate_project_change(project, moved_cutout, contract=contract)
    assert cutout_report["decision"] == "REJECTED"
    assert cutout_report["interface_contract"]["violations"][0]["path"] == "snapshot.center_uv_mm[0]"
    assert "cutout_fit_evidence" in cutout_report["impacts"][0]["invalidated_evidence"]

    standoffs = deepcopy(spec["standoffs"])
    standoffs[0]["center_xy_mm"] = [-19, -12]
    moved_mount = update_project(project, "standoffs", standoffs, reason="move mount")
    with pytest.raises(ValueError, match="1 lock violation"):
        require_protected_interfaces(project, moved_mount, contract)

    resized = update_project(project, "outer_size_mm", [101, 80, 40], reason="resize shell")
    lid_report = evaluate_project_change(project, resized, contract=contract)
    assert lid_report["decision"] == "REJECTED"
    assert any(
        item["selector"]["kind"] == "lid_interface"
        and item["path"] == "snapshot.outer_size_xy_mm[0]"
        for item in lid_report["interface_contract"]["violations"]
    )


def test_declared_numeric_tolerance_is_bounded_and_structural_changes_still_fail() -> None:
    project = _project()
    contract = _contract(project, tolerance=0.1)
    spec = enclosure_spec_to_dict(project.spec)
    cutouts = deepcopy(spec["cutouts"])
    cutouts[0]["center_uv_mm"] = [0.05, 0]
    within = update_project(project, "cutouts", cutouts, reason="allowed alignment correction")
    assert require_protected_interfaces(project, within, contract)["decision"] == "ACCEPTED"

    cutouts[0]["purpose"] = "different connector"
    structural = update_project(project, "cutouts", cutouts, reason="change connector identity")
    report = evaluate_project_change(project, structural, contract=contract)
    assert report["decision"] == "REJECTED"
    assert any(item["code"] == "interface_value_changed" for item in report["interface_contract"]["violations"])

    with pytest.raises(ValueError, match="between 0 and 5"):
        _contract(project, tolerance=5.1)


def test_lineage_and_saved_report_tampering_are_detected() -> None:
    source = _project()
    unrelated = EnclosureProject("other-controller", source.spec)
    report = evaluate_project_change(source, unrelated)
    assert report["decision"] == "REJECTED"
    assert report["lineage"]["valid"] is False

    candidate = update_project(source, "title", "new title", reason="rename")
    report = evaluate_project_change(source, candidate)
    tampered = deepcopy(report)
    tampered["regeneration_required"] = True
    with pytest.raises(ValueError, match="does not recompute"):
        verify_change_impact_report(source, candidate, tampered)


def test_cli_creates_enforces_and_recomputes_interface_evidence(tmp_path: Path) -> None:
    project = _project()
    source = tmp_path / "source.json"
    contract = tmp_path / "contract.json"
    safe = tmp_path / "safe.json"
    blocked = tmp_path / "blocked.json"
    report = tmp_path / "impact.json"
    write_project(source, project)
    base = [sys.executable, "-m", "neurocad_cli", "enclosure"]

    created = subprocess.run(
        [
            *base,
            "interface-lock",
            str(source),
            "--contract-id",
            "controller-v1",
            "--cutout",
            "usb",
            "--lid-interface",
            "-o",
            str(contract),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert created.returncode == 0, created.stderr

    safe_edit = subprocess.run(
        [
            *base,
            "edit",
            str(source),
            "--field",
            "title",
            "--value",
            '"updated controller"',
            "--reason",
            "rename",
            "--interface-contract",
            str(contract),
            "-o",
            str(safe),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert safe_edit.returncode == 0, safe_edit.stderr
    assert json.loads(safe_edit.stdout)["interface_protection"]["valid"] is True

    blocked_edit = subprocess.run(
        [
            *base,
            "edit",
            str(source),
            "--instruction",
            "move cutout usb to 1 x 0 mm",
            "--interface-contract",
            str(contract),
            "-o",
            str(blocked),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert blocked_edit.returncode != 0
    assert not blocked.exists()

    impact = subprocess.run(
        [
            *base,
            "impact-report",
            str(source),
            str(safe),
            "--interface-contract",
            str(contract),
            "-o",
            str(report),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert impact.returncode == 0, impact.stderr
    verified = subprocess.run(
        [
            *base,
            "impact-report-verify",
            str(source),
            str(safe),
            str(report),
            "--interface-contract",
            str(contract),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["valid"] is True
