from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from core.enclosure import EnclosureBuild, EnclosureSpec, LidSpec, build_enclosure
from core.integrations import (
    CapabilityState,
    IntegrationUnavailableError,
    KiCadHandoffError,
    apply_kicad_board_to_project,
    bind_kicad_extraction,
    create_application_handoff,
    create_kicad_extraction_request,
    create_neutral_manifest,
    default_registry,
    export_openscad_bundle,
    parse_kicad_handoff,
    safe_filename_stem,
    verify_exchange_bundle,
    write_application_handoff,
    write_kicad_extraction_request,
    write_neutral_manifest,
)
from core.integrations import exchange as exchange_module
from core.integrations import registry as registry_module
from core.project import EnclosureProject, parse_project, serialize_project


def _build():
    return build_enclosure(
        EnclosureSpec(
            outer_size_mm=(60, 40, 20),
            wall_mm=2,
            profile="fdm_standard",
            lid=LidSpec("friction", thickness_mm=2, clearance_mm=0.3, lip_height_mm=2),
            title="../../Unsafe CASE 🚀",
        )
    )


def _kicad_payload() -> dict:
    return {
        "contract_version": "neurocad-kicad-handoff-v1",
        "units": "mm",
        "source": {
            "name": "controller.kicad_pcb",
            "sha256": "a" * 64,
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
            "connectors": [
                {"id": "J1", "kind": "usb_c", "center_xy_mm": [20, 0], "height_mm": 8},
            ],
            "max_component_height_mm": 10,
        },
    }


def test_registry_distinguishes_native_verified_exchange_and_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONSHAPE_ACCESS_KEY", "must-not-leak-access")
    monkeypatch.setenv("ONSHAPE_SECRET_KEY", "must-not-leak-secret")
    registry = default_registry()
    adapters = registry.describe()
    states = {
        capability.state
        for adapter in adapters
        for capability in adapter.capabilities
    }
    assert states == {
        CapabilityState.NATIVE,
        CapabilityState.VERIFIED,
        CapabilityState.FILE_EXCHANGE,
        CapabilityState.UNAVAILABLE,
    }
    assert registry.get("Fusion 360").id == "fusion"
    serialized = json.dumps(registry.get("onshape").to_dict())
    assert "must-not-leak" not in serialized
    assert "ONSHAPE_ACCESS_KEY" in serialized
    assert registry.get("fusion").capability("native_parametric_document").state is CapabilityState.UNAVAILABLE


@pytest.mark.parametrize(
    "source, expected",
    [
        ("../../Dangerous Name", "dangerous-name"),
        ("CON", "neurocad-con"),
        ("🚀", "neurocad-design"),
    ],
)
def test_safe_filename_stem_removes_path_and_platform_semantics(source: str, expected: str) -> None:
    assert safe_filename_stem(source) == expected
    assert safe_filename_stem("🚀", fallback="../../Fallback") == "fallback"


def test_openscad_bundle_is_safe_atomic_and_truthful(tmp_path: Path) -> None:
    destination = tmp_path / "exchange"
    bundle = export_openscad_bundle(_build(), destination)
    assert bundle.root == destination.resolve()
    assert bundle.manifest["capability"] == {
        "state": "native",
        "native_format": "scad",
        "mesh_kernel_verified": False,
    }
    assert bundle.manifest["external_operation"]["executed"] is False
    spec_path = destination / bundle.manifest["source"]["spec_filename"]
    assert spec_path.is_file()
    assert hashlib.sha256(spec_path.read_bytes()).hexdigest() == bundle.manifest["source"]["spec_sha256"]
    assert {part["id"] for part in bundle.manifest["parts"]} == {"body", "lid"}
    for part in bundle.manifest["parts"]:
        assert part["mesh_verification"] is None
        for artifact in part["artifacts"]:
            assert Path(artifact["filename"]).name == artifact["filename"]
            assert ".." not in artifact["filename"]
            assert (destination / artifact["filename"]).is_file()
    assert not (tmp_path / "unsafe-case-body.scad").exists()
    with pytest.raises(FileExistsError, match="already exists"):
        export_openscad_bundle(_build(), destination)


def test_exchange_rejects_programs_not_derived_from_the_declared_spec(tmp_path: Path) -> None:
    declared = _build()
    other = build_enclosure(
        EnclosureSpec(
            outer_size_mm=(600, 400, 200),
            wall_mm=4,
            profile="fdm_standard",
            lid=LidSpec("friction", 4, 0.3, lip_height_mm=4),
        )
    )
    forged = EnclosureBuild(declared.spec, other.body, other.lid, declared.validation)
    with pytest.raises(ValueError, match="fresh deterministic build"):
        export_openscad_bundle(forged, tmp_path / "forged")


def test_bundle_failure_leaves_no_published_or_staged_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "failed-exchange"

    def fail_compile(*_: object, **__: object) -> None:
        raise RuntimeError("external compiler failed")

    monkeypatch.setattr(exchange_module, "compile_scad_verified", fail_compile)
    with pytest.raises(RuntimeError, match="external compiler failed"):
        export_openscad_bundle(_build(), destination, compile_meshes=True)
    assert not destination.exists()
    assert not list(tmp_path.glob(".*-bundle.*"))


def test_mesh_bundle_fails_before_writing_when_openscad_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry_module.shutil, "which", lambda _: None)
    destination = tmp_path / "unavailable"
    with pytest.raises(IntegrationUnavailableError, match="not detected"):
        export_openscad_bundle(_build(), destination, compile_meshes=True)
    assert not destination.exists()


def test_neutral_and_application_manifests_never_claim_external_success(tmp_path: Path) -> None:
    build = _build()
    bundle = export_openscad_bundle(build, tmp_path / "bundle")
    neutral = create_neutral_manifest(build, bundle=bundle, targets=("openscad", "fusion", "freecad", "blender"))
    assert neutral["external_operation_performed"] is False
    assert neutral["native_documents_created"] == []
    assert neutral["bundle"]["mesh_artifacts_available"] is False
    assert len(neutral["applications"]) == 4

    openscad = create_application_handoff("openscad", bundle)
    assert openscad["handoff"]["ready"] is True
    assert openscad["handoff"]["state"] == "native"
    assert openscad["external_operation_executed"] is False
    freecad = create_application_handoff("freecad", bundle)
    assert freecad["handoff"]["ready"] is True
    assert freecad["handoff"]["state"] == "file_exchange"
    for target in ("fusion", "onshape", "blender", "prusaslicer", "orcaslicer", "bambu_studio", "cura"):
        handoff = create_application_handoff(target, bundle)
        assert handoff["handoff"]["ready"] is False
        assert handoff["handoff"]["state"] == "unavailable"
        assert handoff["native_document_created"] is False

    neutral_path = write_neutral_manifest(tmp_path / "neutral.json", build, bundle=bundle)
    handoff_path = write_application_handoff(tmp_path / "fusion.json", "fusion", bundle)
    assert json.loads(neutral_path.read_text(encoding="utf-8"))["external_operation_performed"] is False
    assert json.loads(handoff_path.read_text(encoding="utf-8"))["handoff"]["ready"] is False
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_application_handoff(handoff_path, "fusion", bundle)


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD is required for verified mesh handoffs")
def test_compiled_bundle_enables_only_verified_mesh_handoffs(tmp_path: Path) -> None:
    bundle = export_openscad_bundle(_build(), tmp_path / "compiled", compile_meshes=True, fn=12)
    assert bundle.compiled_meshes
    assert bundle.manifest["capability"]["state"] == "verified"
    for target in ("fusion", "onshape", "blender", "prusaslicer", "orcaslicer", "bambu_studio", "cura"):
        handoff = create_application_handoff(target, bundle)
        assert handoff["handoff"]["ready"] is True
        assert handoff["handoff"]["state"] == "file_exchange"
        assert {item["format"] for item in handoff["handoff"]["files"]} == {"stl"}
        assert all(item["state"] == "verified" for item in handoff["handoff"]["files"])
        assert handoff["external_operation_executed"] is False

    first_stl = next(bundle.root.glob("*.stl"))
    first_stl.write_bytes(first_stl.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        create_application_handoff("fusion", bundle)


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD is required for request-level re-verification")
def test_handoff_rehashes_spec_and_rechecks_mesh_against_current_request(tmp_path: Path) -> None:
    bundle = export_openscad_bundle(_build(), tmp_path / "compiled", compile_meshes=True, fn=12)
    spec_path = bundle.root / bundle.manifest["source"]["spec_filename"]
    spec_payload = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_payload["outer_size_mm"][0] = 70
    spec_path.write_text(json.dumps(spec_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="specification hash mismatch"):
        create_application_handoff("fusion", bundle)

    manifest_path = bundle.root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["spec_sha256"] = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="declared specification|request-level verification"):
        create_application_handoff("fusion", bundle)


def test_handoff_rebuilds_canonical_source_and_rejects_coherently_rehashed_tampering(tmp_path: Path) -> None:
    bundle = export_openscad_bundle(_build(), tmp_path / "bundle")
    manifest_path = bundle.root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scad_record = next(
        artifact
        for part in manifest["parts"]
        for artifact in part["artifacts"]
        if artifact["format"] == "scad"
    )
    scad_path = bundle.root / scad_record["filename"]
    scad_path.write_text("cube([1, 1, 1]);\n", encoding="utf-8")
    scad_record["bytes"] = scad_path.stat().st_size
    scad_record["sha256"] = hashlib.sha256(scad_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="OpenSCAD artifact does not match"):
        create_application_handoff("openscad", bundle)


def test_exchange_bundle_has_an_independent_positive_verification_report(tmp_path: Path) -> None:
    bundle = export_openscad_bundle(_build(), tmp_path / "bundle", fn=24)
    report = verify_exchange_bundle(bundle)

    assert report["schema_version"] == "neurocad-exchange-verification-v1"
    assert report["valid"] is True
    assert report["bundle"]["schema_version"] == "neurocad-exchange-v2"
    assert report["bundle"]["generator_fn"] == 24
    assert report["bundle"]["part_ids"] == ["body", "lid"]
    assert report["bundle"]["artifact_count"] == 4
    assert report["bundle"]["compiled_meshes"] is False
    assert report["checks"]["kernel_and_request_mesh_verification"] is None
    assert report["external_operation_executed"] is False

    scad_path = next(bundle.root.glob("*.scad"))
    scad_path.write_text("cube([1, 1, 1]);\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_exchange_bundle(bundle)


def test_hardened_handoff_rejects_legacy_exchange_contract(tmp_path: Path) -> None:
    bundle = export_openscad_bundle(_build(), tmp_path / "bundle")
    manifest_path = bundle.root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "neurocad-exchange-v1"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported schema"):
        create_application_handoff("openscad", bundle)


def test_kicad_complete_handoff_converts_only_explicit_board_data() -> None:
    board = parse_kicad_handoff(json.dumps(_kicad_payload()))
    assert board.size_mm == (50.0, 30.0, 1.6)
    assert [hole.id for hole in board.mounting_holes] == ["H1", "H2"]
    assert board.connectors[0].kind == "usb_c"
    assert board.source_hash_verified is False
    with pytest.raises(KiCadHandoffError, match="hash-bound"):
        board.to_pcb_spec()


def test_kicad_handoff_can_bind_receipt_to_the_actual_board(tmp_path: Path) -> None:
    source = tmp_path / "controller.kicad_pcb"
    source.write_text("(kicad_pcb (version 20250101))\n", encoding="utf-8")
    payload = _kicad_payload()
    payload["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    board = parse_kicad_handoff(json.dumps(payload), source_board=source)
    assert board.source_hash_verified is True
    pcb = board.to_pcb_spec()
    assert pcb.mounting_holes_xy_mm == ((-20.0, -10.0), (20.0, 10.0))
    assert pcb.component_height_mm == 10.0

    source.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(KiCadHandoffError, match="hash does not match"):
        parse_kicad_handoff(json.dumps(payload), source_board=source)


def test_reviewed_kicad_extraction_draft_is_bound_without_manual_hash_copying(tmp_path: Path) -> None:
    source = tmp_path / "controller.kicad_pcb"
    source.write_text("(kicad_pcb (version 20250101))\n", encoding="utf-8")
    complete = _kicad_payload()
    draft = {
        "draft_version": "neurocad-kicad-extraction-draft-v1",
        "units": complete["units"],
        "source": {"kicad_version": complete["source"]["kicad_version"]},
        "extraction": complete["extraction"],
        "board": complete["board"],
    }

    receipt = bind_kicad_extraction(json.dumps(draft), source)
    assert receipt["source"]["name"] == source.name
    assert receipt["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert parse_kicad_handoff(json.dumps(receipt), source_board=source).source_hash_verified

    draft["extraction"]["warnings"] = ["unresolved footprint"]
    with pytest.raises(KiCadHandoffError, match="partial KiCad extraction"):
        bind_kicad_extraction(json.dumps(draft), source)


def test_hash_bound_kicad_board_creates_auditable_project_revision(tmp_path: Path) -> None:
    source = tmp_path / "controller.kicad_pcb"
    source.write_text("(kicad_pcb (version 20250101))\n", encoding="utf-8")
    payload = _kicad_payload()
    payload["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    board = parse_kicad_handoff(json.dumps(payload), source_board=source)
    project = EnclosureProject("controller", _build().spec)

    application = apply_kicad_board_to_project(project, board, reason="board revision B")
    assert application.project.revision == 2
    assert application.project.spec.pcb is not None
    assert application.project.spec.pcb.size_mm == (50.0, 30.0, 1.6)
    assert application.project.spec.pcb.mounting_holes_xy_mm == ((-20.0, -10.0), (20.0, 10.0))
    assert board.source_sha256 in application.project.changes[-1].reason
    assert application.project.changes[-1].reason.endswith("; board revision B")
    assert application.to_dict()["automatically_created_cutouts"] is False
    assert application.to_dict()["automatically_created_standoffs"] is False
    assert application.to_dict()["connector_review"][0]["id"] == "J1"
    assert parse_project(serialize_project(application.project)) == application.project

    with pytest.raises(KiCadHandoffError, match="already matches"):
        apply_kicad_board_to_project(application.project, board)


@pytest.mark.parametrize("mutation, message", [
    (lambda value: value["extraction"].update(complete=False), "partial KiCad extraction"),
    (lambda value: value["extraction"]["warnings"].append("zones omitted"), "partial KiCad extraction"),
    (lambda value: value["extraction"]["complete_fields"].pop(), "every required board field"),
    (lambda value: value["board"]["outline"].update(kind="polygon"), "rectangular"),
    (lambda value: value["source"].update(name="../../board.kicad_pcb"), "basename"),
    (lambda value: value["source"].update(name="board.json"), "kicad_pcb"),
    (lambda value: value["board"]["mounting_holes"][0].update(center_xy_mm=[30, 0]), "outside"),
])
def test_kicad_handoff_fails_closed_on_partial_or_unsupported_data(mutation, message: str) -> None:
    payload = copy.deepcopy(_kicad_payload())
    mutation(payload)
    with pytest.raises(KiCadHandoffError, match=message):
        parse_kicad_handoff(json.dumps(payload))


def test_kicad_extraction_request_is_a_non_execution_receipt(tmp_path: Path) -> None:
    board_path = tmp_path / "controller.kicad_pcb"
    board_path.write_text("(kicad_pcb (version 20250101))\n", encoding="utf-8")
    request = create_kicad_extraction_request(board_path)
    assert request["status"] == "external_extraction_required"
    assert request["operation_executed"] is False
    assert request["raw_board_parsed"] is False
    assert request["source"]["name"] == "controller.kicad_pcb"
    assert len(request["source"]["sha256"]) == 64
    output = write_kicad_extraction_request(tmp_path / "request.json", board_path)
    assert json.loads(output.read_text(encoding="utf-8"))["operation_executed"] is False
