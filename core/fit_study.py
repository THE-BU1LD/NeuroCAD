"""Atomic, source-bound physical-fit study bundles for supported enclosure cutouts.

This module creates geometry and evidence templates. It never claims that a
coupon was printed, measured, or physically accepted.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import shutil
import tempfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .fit_sample import cutout_fit_sample
from .gmsh_integrity import publish_directory_noreplace
from .ir_export import program_to_scad
from .ir_parser import parse_ir_json, serialize_ir_json
from .json_io import strict_json_loads
from .project import EnclosureProject, parse_project, serialize_project

FIT_STUDY_VERSION = "neurocad-fit-study-v2"
FIT_OBSERVATIONS_VERSION = "neurocad-fit-observations-v2"
FIT_REPORT_VERSION = "neurocad-fit-report-v2"
FIT_MANIFEST_VERSION = "neurocad-fit-study-manifest-v2"
FIT_EVIDENCE_MANIFEST_VERSION = "neurocad-fit-evidence-manifest-v1"
MAX_FIT_STUDY_FILE_BYTES = 1_048_576
MAX_EVIDENCE_FILE_BYTES = 16 * 1_048_576
MAX_EVIDENCE_TOTAL_BYTES = 64 * 1_048_576
MAX_EVIDENCE_FILES = 32
MAX_VARIANTS = 21
MAX_REPLICATES = 20
SCAD_FN = 96
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
VARIANT_ID_PATTERN = re.compile(r"^variant-[0-9]{2}$")
ADJUSTMENT_DEFINITION = (
    "total diameter adjustment for circular apertures; total width and height adjustment "
    "for rectangular apertures"
)
ACCEPTANCE_RULE = (
    "A variant passes only when every predeclared replicate succeeds under the recorded acceptance criterion; "
    "any failed replicate makes that variant fail."
)

LIMITATIONS = (
    "The bundle contains generated coupon geometry and blank evidence templates; it does not show that anything was printed or measured.",
    "Opening adjustment is applied to the compiled aperture, not to the nominal enclosure requirement.",
    "Observed fit applies only to the recorded printer, material, slicer, orientation, settings, instrument, and environment.",
    "A successful coupon is not evidence of assembly access, structural strength, long-term stability, safety, or regulatory compliance.",
    "Wilson intervals summarize retained binary trials; they are descriptive and are not a guarantee for another part or process.",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _bounded_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"fit-study artifact must be a regular file: {path.name}")
    size = path.stat().st_size
    if size > MAX_FIT_STUDY_FILE_BYTES:
        raise ValueError(f"fit-study artifact exceeds {MAX_FIT_STUDY_FILE_BYTES} bytes: {path.name}")
    return path.read_bytes()


def _strict_json_file(path: Path) -> Any:
    raw = _bounded_bytes(path)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"fit-study artifact is not UTF-8: {path.name}") from exc
    return strict_json_loads(text)


def _finite(value: object, label: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted) or not minimum <= converted <= maximum:
        raise ValueError(f"{label} must be between {minimum:g} and {maximum:g}")
    return converted


def _text(value: object, label: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be a non-empty string of at most {maximum} characters")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{label} must not contain control characters")
    return value.strip()


def _timestamp(value: object, label: str) -> str:
    text = _text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include an explicit UTC offset")
    return text


def _evidence_text(value: object, label: str, *, maximum: int = 256) -> str:
    text = _text(value, label, maximum=maximum)
    if text.upper().startswith("REQUIRED"):
        raise ValueError(f"{label} still contains the blank-template placeholder")
    return text


def _dimension_pair(value: object, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError(f"{label} must contain exactly two dimensions")
    return [
        _finite(value[index], f"{label}[{index}]", minimum=0.1, maximum=100000)
        for index in range(2)
    ]


def _exact_keys(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    missing, extra = sorted(keys - set(value)), sorted(set(value) - keys)
    if missing:
        raise ValueError(f"{label} is missing keys: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported keys: {', '.join(extra)}")
    return value


def normalize_adjustments(values: Iterable[float]) -> tuple[float, ...]:
    adjustments = tuple(_finite(value, "aperture adjustment", minimum=-5, maximum=5) for value in values)
    if not 2 <= len(adjustments) <= MAX_VARIANTS:
        raise ValueError(f"fit study requires 2 to {MAX_VARIANTS} aperture adjustments")
    if len(set(adjustments)) != len(adjustments):
        raise ValueError("fit-study aperture adjustments must be unique")
    return tuple(sorted(adjustments))


def _replicate_count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("replicates per variant must be an integer")
    if not 1 <= value <= MAX_REPLICATES:
        raise ValueError(f"replicates per variant must be between 1 and {MAX_REPLICATES}")
    return value


def _wilson_interval(successes: int, attempts: int) -> list[float]:
    """Return the two-sided 95% Wilson score interval for a binary proportion."""
    if not 0 <= successes <= attempts or attempts < 1:
        raise ValueError("Wilson interval requires 0 <= successes <= attempts and attempts >= 1")
    z = 1.959963984540054
    proportion = successes / attempts
    denominator = 1 + z * z / attempts
    centre = (proportion + z * z / (2 * attempts)) / denominator
    half_width = z * math.sqrt(
        proportion * (1 - proportion) / attempts + z * z / (4 * attempts * attempts)
    ) / denominator
    return [max(0.0, centre - half_width), min(1.0, centre + half_width)]


def _worksheet(study: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    fields = [
        "variant_id",
        "trial_id",
        "aperture_adjustment_mm",
        "nominal_width_mm",
        "nominal_height_mm",
        "generated_width_mm",
        "generated_height_mm",
        "fit_succeeded",
        "measured_width_mm",
        "measured_height_mm",
        "notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for variant in study["variants"]:
        for replicate in range(1, study["replicates_per_variant"] + 1):
            writer.writerow(
                {
                    "variant_id": variant["variant_id"],
                    "trial_id": f"trial-{replicate:02d}",
                    "aperture_adjustment_mm": variant["aperture_adjustment_mm"],
                    "nominal_width_mm": variant["nominal_aperture_size_mm"][0],
                    "nominal_height_mm": variant["nominal_aperture_size_mm"][1],
                    "generated_width_mm": variant["aperture_size_mm"][0],
                    "generated_height_mm": variant["aperture_size_mm"][1],
                }
            )
    return output.getvalue()


def _observation_template(study: dict[str, Any], *, study_binding_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": FIT_OBSERVATIONS_VERSION,
        "study_binding_sha256": study_binding_sha256,
        "passport": {
            "printer_id": "REQUIRED",
            "printer_model": "REQUIRED",
            "printer_firmware": "REQUIRED",
            "nozzle_diameter_mm": None,
            "material_vendor": "REQUIRED",
            "material_product": "REQUIRED",
            "material_lot": "REQUIRED",
            "slicer": "REQUIRED",
            "slicer_version": "REQUIRED",
            "process_profile": "REQUIRED",
            "layer_height_mm": None,
            "extrusion_width_mm": None,
            "orientation": "REQUIRED",
            "mating_part_id": "REQUIRED",
            "mating_part_reference": "REQUIRED drawing, measurement record, or retained artifact",
            "instrument": "REQUIRED",
            "instrument_calibration_id": "REQUIRED",
            "measurement_resolution_mm": None,
            "environment": "REQUIRED temperature/humidity or explicit unavailable note",
            "operator_id": "REQUIRED pseudonymous identifier",
            "measured_at": "REQUIRED ISO-8601 timestamp",
            "acceptance_criterion": "REQUIRED predeclared operational fit criterion",
            "trial_protocol": "REQUIRED insertion order, force handling, and reset procedure",
        },
        "observations": [
            {
                "variant_id": variant["variant_id"],
                "trial_id": f"trial-{replicate:02d}",
                "fit_succeeded": None,
                "measured_width_mm": None,
                "measured_height_mm": None,
                "notes": "",
            }
            for variant in study["variants"]
            for replicate in range(1, study["replicates_per_variant"] + 1)
        ],
    }


def create_fit_study_bundle(
    project: EnclosureProject,
    cutout_id: str,
    output_dir: Path,
    *,
    adjustments_mm: Iterable[float],
    margin_mm: float = 5.0,
    replicates_per_variant: int = 3,
) -> dict[str, Any]:
    """Generate and atomically publish a complete fit-study bundle."""
    project = parse_project(serialize_project(project))
    adjustments = normalize_adjustments(adjustments_mm)
    replicates = _replicate_count(replicates_per_variant)
    if margin_mm < 5:
        raise ValueError("fit-study variants require at least 5 mm of margin for physical identity markers")
    destination_input = output_dir.expanduser()
    destination = destination_input.parent.resolve() / destination_input.name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"fit-study output directory already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    project_bytes = serialize_project(project).encode("utf-8")
    project_sha256 = _sha256_bytes(project_bytes)
    try:
        write_text_atomic(staging / "source-project.ncad.json", project_bytes.decode("utf-8"))
        variants: list[dict[str, Any]] = []
        samples = []
        for index, adjustment in enumerate(adjustments, start=1):
            sample = cutout_fit_sample(
                project,
                cutout_id,
                margin_mm=margin_mm,
                aperture_adjustment_mm=adjustment,
                marker_code=index,
            )
            samples.append(sample)
            variant_id = f"variant-{index:02d}"
            artifact = f"{variant_id}.ncad.json"
            scad_artifact = f"{variant_id}.scad"
            encoded = serialize_ir_json(sample).encode("utf-8")
            scad_encoded = program_to_scad(sample, fn=SCAD_FN).encode("utf-8")
            write_text_atomic(staging / artifact, encoded.decode("utf-8"))
            write_text_atomic(staging / scad_artifact, scad_encoded.decode("utf-8"))
            variants.append(
                {
                    "variant_id": variant_id,
                    "physical_marker_code": index,
                    "artifact": artifact,
                    "artifact_sha256": _sha256_bytes(encoded),
                    "scad_artifact": scad_artifact,
                    "scad_sha256": _sha256_bytes(scad_encoded),
                    "aperture_adjustment_mm": adjustment,
                    "nominal_aperture_size_mm": sample.metadata["nominal_aperture_size_mm"],
                    "aperture_size_mm": sample.metadata["aperture_size_mm"],
                }
            )
        study = {
            "schema_version": FIT_STUDY_VERSION,
            "source_project_id": project.project_id,
            "source_project_revision": project.revision,
            "source_project_sha256": project_sha256,
            "source_cutout_id": cutout_id,
            "source_face": samples[0].metadata["source_face"],
            "margin_mm": float(margin_mm),
            "replicates_per_variant": replicates,
            "acceptance_rule": ACCEPTANCE_RULE,
            "scad_fn": SCAD_FN,
            "adjustment_definition": ADJUSTMENT_DEFINITION,
            "variants": variants,
            "limitations": list(LIMITATIONS),
        }
        study_text = _canonical_json(study)
        write_text_atomic(staging / "study.json", study_text)
        write_text_atomic(staging / "measurement-worksheet.csv", _worksheet(study))
        study_binding_sha256 = _sha256_bytes(
            _canonical_json(
                {
                    "source_project_sha256": project_sha256,
                    "study_sha256": _sha256_bytes(study_text.encode("utf-8")),
                    "variants": {item["artifact"]: item["artifact_sha256"] for item in variants},
                }
            ).encode("utf-8")
        )
        write_text_atomic(
            staging / "observations.template.json",
            _canonical_json(_observation_template(study, study_binding_sha256=study_binding_sha256)),
        )
        readme = (
            "# NeuroCAD fit study\n\n"
            "This directory contains generated fit coupons and blank evidence templates. "
            "Each variant includes deterministic `.ncad.json` and directly printable OpenSCAD source. "
            "Manufacture every predeclared replicate under one recorded process, enter every outcome into a "
            "copy of `observations.template.json`, and run "
            "`neurocad enclosure fit-study-evaluate`. Blank templates are not measurements.\n\n"
            "Opening adjustment is a total diameter change for circular apertures and a total width/height "
            "change for rectangular apertures. A fixed anchor and five binary holes encode each variant ID in "
            "the top margin. Preserve failed parts, every replicate, and non-monotone results.\n"
        )
        write_text_atomic(staging / "README.md", readme)
        artifact_names = sorted(path.name for path in staging.iterdir())
        hashes = {name: _sha256_bytes(_bounded_bytes(staging / name)) for name in artifact_names}
        manifest = {
            "schema_version": FIT_MANIFEST_VERSION,
            "study_sha256": hashes["study.json"],
            "study_binding_sha256": study_binding_sha256,
            "source_project_sha256": project_sha256,
            "files": hashes,
            "external_measurements_present": False,
            "physical_fit_claimed": False,
        }
        write_text_atomic(staging / "manifest.json", _canonical_json(manifest))
        publish_directory_noreplace(staging, destination)
        return {**manifest, "output_dir": str(destination), "manifest_sha256": _sha256_bytes((destination / "manifest.json").read_bytes())}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_fit_study_bundle(bundle: Path, *, expected_project: EnclosureProject | None = None) -> dict[str, Any]:
    requested_root = bundle.expanduser()
    if requested_root.is_symlink():
        raise ValueError("fit-study bundle directory must not be a symbolic link")
    root = requested_root.resolve()
    if not root.is_dir():
        raise ValueError("fit-study bundle must be a regular directory")
    manifest = _strict_json_file(root / "manifest.json")
    manifest = _exact_keys(
        manifest,
        {
            "schema_version", "study_sha256", "study_binding_sha256", "source_project_sha256", "files",
            "external_measurements_present", "physical_fit_claimed",
        },
        "manifest",
    )
    if manifest["schema_version"] != FIT_MANIFEST_VERSION:
        raise ValueError("unsupported fit-study manifest version")
    if manifest["external_measurements_present"] is not False or manifest["physical_fit_claimed"] is not False:
        raise ValueError("generated fit-study manifest must not claim external measurements or physical fit")
    for field in ("study_sha256", "study_binding_sha256", "source_project_sha256"):
        if not isinstance(manifest[field], str) or SHA256_PATTERN.fullmatch(manifest[field]) is None:
            raise ValueError(f"manifest.{field} must be a lowercase SHA-256")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError("manifest.files must be a non-empty object")
    expected_names = set(files) | {"manifest.json"}
    actual_names = {path.name for path in root.iterdir()}
    if actual_names != expected_names:
        raise ValueError("fit-study bundle contains missing or unexpected files")
    for name, expected_hash in files.items():
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or not isinstance(expected_hash, str)
            or SHA256_PATTERN.fullmatch(expected_hash) is None
        ):
            raise ValueError("manifest contains an invalid file entry")
        if _sha256_bytes(_bounded_bytes(root / name)) != expected_hash:
            raise ValueError(f"fit-study artifact hash mismatch: {name}")
    study = _exact_keys(
        _strict_json_file(root / "study.json"),
        {
            "schema_version", "source_project_id", "source_project_revision", "source_project_sha256",
            "source_cutout_id", "source_face", "margin_mm", "replicates_per_variant", "acceptance_rule",
            "scad_fn", "adjustment_definition", "variants", "limitations",
        },
        "study",
    )
    if study["schema_version"] != FIT_STUDY_VERSION:
        raise ValueError("unsupported fit-study document version")
    if _sha256_bytes(_bounded_bytes(root / "study.json")) != manifest["study_sha256"]:
        raise ValueError("study hash does not match manifest")
    if study.get("source_project_sha256") != manifest["source_project_sha256"]:
        raise ValueError("study source project hash does not match manifest")
    source_project_bytes = _bounded_bytes(root / "source-project.ncad.json")
    if _sha256_bytes(source_project_bytes) != manifest["source_project_sha256"]:
        raise ValueError("bundled source project hash does not match manifest")
    try:
        source_project = parse_project(source_project_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("bundled source project is not UTF-8") from exc
    if serialize_project(source_project).encode("utf-8") != source_project_bytes:
        raise ValueError("bundled source project is not canonical")
    if isinstance(study["source_project_revision"], bool) or not isinstance(study["source_project_revision"], int):
        raise TypeError("study source project revision must be an integer")
    if source_project.project_id != study["source_project_id"] or source_project.revision != study["source_project_revision"]:
        raise ValueError("study project identity does not match bundled source project")
    if not isinstance(study["source_cutout_id"], str) or not study["source_cutout_id"]:
        raise ValueError("study source cutout ID must be a non-empty string")
    _finite(study["margin_mm"], "study.margin_mm", minimum=2, maximum=50)
    if study["margin_mm"] < 5:
        raise ValueError("fit-study margin is too small for physical identity markers")
    _replicate_count(study["replicates_per_variant"])
    if study["acceptance_rule"] != ACCEPTANCE_RULE:
        raise ValueError("fit-study acceptance rule was changed")
    if study["scad_fn"] != SCAD_FN:
        raise ValueError("fit-study OpenSCAD facet policy was changed")
    if study["adjustment_definition"] != ADJUSTMENT_DEFINITION:
        raise ValueError("fit-study aperture adjustment definition was changed")
    if study["limitations"] != list(LIMITATIONS):
        raise ValueError("fit-study limitations were changed")
    variants = study.get("variants")
    if not isinstance(variants, list) or not 2 <= len(variants) <= MAX_VARIANTS:
        raise ValueError("study must contain 2 to 21 variants")
    variant_ids: set[str] = set()
    artifacts: set[str] = set()
    adjustments: list[float] = []
    for index, variant in enumerate(variants, start=1):
        variant = _exact_keys(
            variant,
            {
                "variant_id", "physical_marker_code", "artifact", "artifact_sha256",
                "scad_artifact", "scad_sha256", "aperture_adjustment_mm",
                "nominal_aperture_size_mm", "aperture_size_mm",
            },
            "study variant",
        )
        variant_id, artifact = variant.get("variant_id"), variant.get("artifact")
        if (
            not isinstance(variant_id, str)
            or VARIANT_ID_PATTERN.fullmatch(variant_id) is None
            or variant_id != f"variant-{index:02d}"
            or variant_id in variant_ids
        ):
            raise ValueError("study variant IDs must be unique ordered strings")
        variant_ids.add(variant_id)
        if variant.get("physical_marker_code") != index:
            raise ValueError(f"study variant physical marker code mismatch: {variant_id}")
        if not isinstance(artifact, str) or artifact not in files:
            raise ValueError("study variant references an undeclared artifact")
        if artifact in artifacts:
            raise ValueError("study variants must reference unique artifacts")
        artifacts.add(artifact)
        if variant.get("artifact_sha256") != files[artifact]:
            raise ValueError(f"study variant artifact hash mismatch: {variant_id}")
        scad_artifact = variant.get("scad_artifact")
        if not isinstance(scad_artifact, str) or scad_artifact not in files or scad_artifact in artifacts:
            raise ValueError("study variant references an invalid or duplicate OpenSCAD artifact")
        artifacts.add(scad_artifact)
        if variant.get("scad_sha256") != files[scad_artifact]:
            raise ValueError(f"study variant OpenSCAD hash mismatch: {variant_id}")
        adjustment = _finite(
            variant["aperture_adjustment_mm"],
            f"{variant_id}.aperture_adjustment_mm",
            minimum=-5,
            maximum=5,
        )
        adjustments.append(adjustment)
        artifact_bytes = _bounded_bytes(root / artifact)
        program = parse_ir_json(artifact_bytes.decode("utf-8"))
        metadata = program.metadata
        if metadata.get("source_project_sha256") != manifest["source_project_sha256"]:
            raise ValueError(f"variant source project mismatch: {variant_id}")
        if metadata.get("source_cutout_id") != study.get("source_cutout_id"):
            raise ValueError(f"variant source cutout mismatch: {variant_id}")
        if metadata.get("aperture_adjustment_mm") != variant.get("aperture_adjustment_mm"):
            raise ValueError(f"variant aperture adjustment mismatch: {variant_id}")
        marker = metadata.get("physical_marker")
        if not isinstance(marker, dict) or marker.get("code") != index:
            raise ValueError(f"variant physical marker metadata mismatch: {variant_id}")
        aperture_node = next((node for node in program.nodes if node.id == "sample_aperture"), None)
        if aperture_node is None or aperture_node.primitive is None:
            raise ValueError(f"variant has no sample aperture geometry: {variant_id}")
        if aperture_node.primitive.kind == "cylinder":
            diameter = 2 * float(aperture_node.primitive.parameters["radius"])
            measured_size = [diameter, diameter]
        elif aperture_node.primitive.kind == "box":
            size = aperture_node.primitive.parameters["size"]
            measured_size = [float(size[0]), float(size[1])]
        else:
            raise ValueError(f"variant has unsupported sample aperture geometry: {variant_id}")
        if measured_size != variant.get("aperture_size_mm") or measured_size != metadata.get("aperture_size_mm"):
            raise ValueError(f"variant aperture label does not match generated geometry: {variant_id}")
        nominal = _dimension_pair(
            variant.get("nominal_aperture_size_mm"),
            f"{variant_id}.nominal_aperture_size_mm",
        )
        declared_size = _dimension_pair(variant.get("aperture_size_mm"), f"{variant_id}.aperture_size_mm")
        if declared_size != measured_size:
            raise ValueError(f"variant aperture dimensions do not match generated geometry: {variant_id}")
        if any(nominal[index] + adjustment != measured_size[index] for index in range(2)):
            raise ValueError(f"variant aperture adjustment does not match generated geometry: {variant_id}")
        regenerated = cutout_fit_sample(
            source_project,
            study["source_cutout_id"],
            margin_mm=float(study["margin_mm"]),
            aperture_adjustment_mm=adjustment,
            marker_code=index,
        )
        if serialize_ir_json(regenerated).encode("utf-8") != artifact_bytes:
            raise ValueError(f"variant does not regenerate from the bundled source project: {variant_id}")
        expected_scad = program_to_scad(regenerated, fn=SCAD_FN).encode("utf-8")
        if _bounded_bytes(root / scad_artifact) != expected_scad:
            raise ValueError(f"variant OpenSCAD does not regenerate from canonical IR: {variant_id}")
    if tuple(adjustments) != normalize_adjustments(adjustments):
        raise ValueError("study variants must use unique increasing adjustments")
    required_files = {
        "README.md",
        "measurement-worksheet.csv",
        "observations.template.json",
        "source-project.ncad.json",
        "study.json",
        *artifacts,
    }
    if set(files) != required_files:
        raise ValueError("fit-study manifest inventory does not match the declared study artifacts")
    recomputed_binding = _sha256_bytes(
        _canonical_json(
            {
                "source_project_sha256": manifest["source_project_sha256"],
                "study_sha256": manifest["study_sha256"],
                "variants": {item["artifact"]: item["artifact_sha256"] for item in variants},
            }
        ).encode("utf-8")
    )
    if recomputed_binding != manifest["study_binding_sha256"]:
        raise ValueError("fit-study binding hash does not match source, study, and variants")
    template = _strict_json_file(root / "observations.template.json")
    expected_template = _observation_template(study, study_binding_sha256=recomputed_binding)
    if template != expected_template:
        raise ValueError("observation template is not bound to this fit study")
    if _bounded_bytes(root / "measurement-worksheet.csv").decode("utf-8") != _worksheet(study):
        raise ValueError("measurement worksheet does not match the fit study")
    if expected_project is not None:
        canonical_expected = parse_project(serialize_project(expected_project))
        expected_hash = _sha256_bytes(serialize_project(canonical_expected).encode("utf-8"))
        if expected_hash != manifest["source_project_sha256"]:
            raise ValueError("fit-study bundle does not match the expected project revision")
    return {
        "valid": True,
        "schema_version": manifest["schema_version"],
        "manifest_sha256": _sha256_bytes(_bounded_bytes(root / "manifest.json")),
        "study_sha256": manifest["study_sha256"],
        "study_binding_sha256": manifest["study_binding_sha256"],
        "source_project_sha256": manifest["source_project_sha256"],
        "variant_count": len(variants),
        "external_measurements_present": False,
        "physical_fit_claimed": False,
    }


def evaluate_fit_study(bundle: Path, observations_document: object) -> dict[str, Any]:
    verification = verify_fit_study_bundle(bundle)
    root = bundle.expanduser().resolve()
    study = _strict_json_file(root / "study.json")
    document = _exact_keys(
        observations_document,
        {"schema_version", "study_binding_sha256", "passport", "observations"},
        "observations document",
    )
    if document["schema_version"] != FIT_OBSERVATIONS_VERSION:
        raise ValueError("unsupported fit-observations version")
    if document["study_binding_sha256"] != verification["study_binding_sha256"]:
        raise ValueError("observations are not bound to this exact fit-study geometry and source identity")
    passport = dict(
        _exact_keys(
            document["passport"],
            {
                "printer_id", "printer_model", "printer_firmware", "nozzle_diameter_mm", "material_vendor",
                "material_product", "material_lot", "slicer", "slicer_version", "process_profile",
                "layer_height_mm", "extrusion_width_mm", "orientation", "mating_part_id",
                "mating_part_reference", "instrument", "instrument_calibration_id",
                "measurement_resolution_mm", "environment", "operator_id", "measured_at",
                "acceptance_criterion", "trial_protocol",
            },
            "passport",
        )
    )
    for key in (
        "printer_id", "printer_model", "printer_firmware", "material_vendor", "material_product", "material_lot",
        "slicer", "slicer_version", "process_profile", "orientation", "mating_part_id", "mating_part_reference",
        "instrument", "instrument_calibration_id", "environment", "operator_id", "acceptance_criterion",
        "trial_protocol",
    ):
        passport[key] = _evidence_text(passport[key], f"passport.{key}")
    passport["measured_at"] = _timestamp(passport["measured_at"], "passport.measured_at")
    passport["nozzle_diameter_mm"] = _finite(
        passport["nozzle_diameter_mm"], "passport.nozzle_diameter_mm", minimum=0.1, maximum=2
    )
    passport["layer_height_mm"] = _finite(
        passport["layer_height_mm"], "passport.layer_height_mm", minimum=0.01, maximum=2
    )
    passport["extrusion_width_mm"] = _finite(
        passport["extrusion_width_mm"], "passport.extrusion_width_mm", minimum=0.05, maximum=5
    )
    passport["measurement_resolution_mm"] = _finite(
        passport["measurement_resolution_mm"], "passport.measurement_resolution_mm", minimum=0.001, maximum=1
    )
    variants = {item["variant_id"]: item for item in study["variants"]}
    replicates = _replicate_count(study["replicates_per_variant"])
    raw_observations = document["observations"]
    if not isinstance(raw_observations, list):
        raise TypeError("observations must be an array")
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    expected_trial_ids = {f"trial-{replicate:02d}" for replicate in range(1, replicates + 1)}
    for index, raw in enumerate(raw_observations):
        item = _exact_keys(
            raw,
            {"variant_id", "trial_id", "fit_succeeded", "measured_width_mm", "measured_height_mm", "notes"},
            f"observations[{index}]",
        )
        variant_id = _text(item["variant_id"], f"observations[{index}].variant_id")
        if variant_id not in variants:
            raise ValueError(f"unknown fit-study variant: {variant_id}")
        trial_id = _text(item["trial_id"], f"observations[{index}].trial_id")
        if trial_id not in expected_trial_ids:
            raise ValueError(f"unknown fit-study trial for {variant_id}: {trial_id}")
        identity = (variant_id, trial_id)
        if identity in seen:
            raise ValueError(f"duplicate fit-study observation: {variant_id}/{trial_id}")
        seen.add(identity)
        if not isinstance(item["fit_succeeded"], bool):
            raise TypeError(f"observations[{index}].fit_succeeded must be a boolean")
        measured: dict[str, float | None] = {}
        for key in ("measured_width_mm", "measured_height_mm"):
            value = item[key]
            measured[key] = (
                None
                if value is None
                else _finite(value, f"observations[{index}].{key}", minimum=0.01, maximum=100000)
            )
        if (measured["measured_width_mm"] is None) != (measured["measured_height_mm"] is None):
            raise ValueError(
                f"observations[{index}] must provide both measured aperture dimensions or leave both unknown"
            )
        notes = item["notes"]
        if (
            not isinstance(notes, str)
            or len(notes) > 1024
            or any(ord(character) < 32 and character not in "\n\t" for character in notes)
        ):
            raise ValueError(f"observations[{index}].notes must be a string of at most 1024 characters")
        observations.append(
            {
                "variant_id": variant_id,
                "trial_id": trial_id,
                "aperture_adjustment_mm": variants[variant_id]["aperture_adjustment_mm"],
                "fit_succeeded": item["fit_succeeded"],
                **measured,
                "notes": notes,
            }
        )
    expected = {
        (variant_id, f"trial-{replicate:02d}")
        for variant_id in variants
        for replicate in range(1, replicates + 1)
    }
    missing = sorted(expected - seen)
    if missing:
        formatted = ", ".join(f"{variant_id}/{trial_id}" for variant_id, trial_id in missing)
        raise ValueError(f"complete fit-study observations are required; missing: {formatted}")
    ordered = sorted(observations, key=lambda item: (item["aperture_adjustment_mm"], item["trial_id"]))
    variant_results: list[dict[str, Any]] = []
    for variant_id, variant in variants.items():
        trials = [item for item in ordered if item["variant_id"] == variant_id]
        success_count = sum(1 for item in trials if item["fit_succeeded"])
        variant_results.append(
            {
                "variant_id": variant_id,
                "aperture_adjustment_mm": variant["aperture_adjustment_mm"],
                "attempts": len(trials),
                "successes": success_count,
                "failures": len(trials) - success_count,
                "success_rate": success_count / len(trials),
                "success_rate_wilson_95": _wilson_interval(success_count, len(trials)),
                "fit_succeeded": success_count == len(trials),
            }
        )
    variant_results.sort(key=lambda item: item["aperture_adjustment_mm"])
    violations: list[dict[str, object]] = []
    for earlier_index, earlier in enumerate(variant_results):
        if not earlier["fit_succeeded"]:
            continue
        for later in variant_results[earlier_index + 1 :]:
            if not later["fit_succeeded"]:
                violations.append({"smaller_success": earlier["variant_id"], "larger_failure": later["variant_id"]})
    failures = [item["aperture_adjustment_mm"] for item in variant_results if not item["fit_succeeded"]]
    successes = [item["aperture_adjustment_mm"] for item in variant_results if item["fit_succeeded"]]
    if violations:
        disposition = "NON_MONOTONE_INCONSISTENT"
        recommendation = None
    elif failures and successes:
        disposition = "BRACKETED_OBSERVED_TRANSITION"
        recommendation = min(successes)
    elif successes:
        disposition = "SUCCESS_AT_OR_BELOW_TESTED_RANGE"
        recommendation = min(successes)
    else:
        disposition = "NO_SUCCESS_WITHIN_TESTED_RANGE"
        recommendation = None
    normalized_observations = [
        {
            "variant_id": item["variant_id"],
            "trial_id": item["trial_id"],
            "fit_succeeded": item["fit_succeeded"],
            "measured_width_mm": item["measured_width_mm"],
            "measured_height_mm": item["measured_height_mm"],
            "notes": item["notes"],
        }
        for item in ordered
    ]
    normalized_document = {
        "schema_version": FIT_OBSERVATIONS_VERSION,
        "study_binding_sha256": verification["study_binding_sha256"],
        "passport": passport,
        "observations": normalized_observations,
    }
    return {
        "schema_version": FIT_REPORT_VERSION,
        "fit_study_manifest_sha256": verification["manifest_sha256"],
        "fit_study_binding_sha256": verification["study_binding_sha256"],
        "canonical_observations_sha256": _sha256_bytes(_canonical_json(normalized_document).encode("utf-8")),
        "source_project_sha256": verification["source_project_sha256"],
        "passport": passport,
        "observations": ordered,
        "variant_results": variant_results,
        "acceptance_rule": ACCEPTANCE_RULE,
        "disposition": disposition,
        "observed_failure_edge_mm": max(failures) if failures else None,
        "observed_success_edge_mm": min(successes) if successes else None,
        "recommended_tested_adjustment_mm": recommendation,
        "non_monotone_violations": violations,
        "limitations": list(LIMITATIONS),
        "physical_fit_certified": False,
    }


def verify_fit_study_report(bundle: Path, report_document: object) -> dict[str, Any]:
    """Recompute a saved report from its retained observations and exact study."""
    report = _exact_keys(
        report_document,
        {
            "schema_version", "fit_study_manifest_sha256", "fit_study_binding_sha256",
            "canonical_observations_sha256", "source_project_sha256", "passport", "observations",
            "variant_results", "acceptance_rule",
            "disposition", "observed_failure_edge_mm", "observed_success_edge_mm",
            "recommended_tested_adjustment_mm", "non_monotone_violations", "limitations",
            "physical_fit_certified",
        },
        "fit-study report",
    )
    if report["schema_version"] != FIT_REPORT_VERSION:
        raise ValueError("unsupported fit-study report version")
    observations = report["observations"]
    if not isinstance(observations, list):
        raise TypeError("fit-study report observations must be an array")
    reconstructed: list[dict[str, Any]] = []
    for index, observation in enumerate(observations):
        item = _exact_keys(
            observation,
            {
                "variant_id", "trial_id", "aperture_adjustment_mm", "fit_succeeded",
                "measured_width_mm", "measured_height_mm", "notes",
            },
            f"fit-study report observations[{index}]",
        )
        reconstructed.append(
            {
                "variant_id": item["variant_id"],
                "trial_id": item["trial_id"],
                "fit_succeeded": item["fit_succeeded"],
                "measured_width_mm": item["measured_width_mm"],
                "measured_height_mm": item["measured_height_mm"],
                "notes": item["notes"],
            }
        )
    observations_document = {
        "schema_version": FIT_OBSERVATIONS_VERSION,
        "study_binding_sha256": report["fit_study_binding_sha256"],
        "passport": report["passport"],
        "observations": reconstructed,
    }
    recomputed = evaluate_fit_study(bundle, observations_document)
    if recomputed != report:
        raise ValueError("fit-study report does not recompute from its retained observations and bundle")
    return {
        "valid": True,
        "schema_version": FIT_REPORT_VERSION,
        "report_sha256": _sha256_bytes(_canonical_json(report).encode("utf-8")),
        "fit_study_manifest_sha256": report["fit_study_manifest_sha256"],
        "disposition": report["disposition"],
        "physical_fit_certified": False,
    }


def _observations_from_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FIT_OBSERVATIONS_VERSION,
        "study_binding_sha256": report["fit_study_binding_sha256"],
        "passport": report["passport"],
        "observations": [
            {
                "variant_id": item["variant_id"],
                "trial_id": item["trial_id"],
                "fit_succeeded": item["fit_succeeded"],
                "measured_width_mm": item["measured_width_mm"],
                "measured_height_mm": item["measured_height_mm"],
                "notes": item["notes"],
            }
            for item in report["observations"]
        ],
    }


def _evidence_source(path: Path) -> tuple[str, bytes]:
    source = path.expanduser()
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"evidence attachment must be a regular non-symlink file: {source}")
    name = _text(source.name, "evidence attachment filename", maximum=255)
    size = source.stat().st_size
    if size <= 0 or size > MAX_EVIDENCE_FILE_BYTES:
        raise ValueError(
            f"evidence attachment must contain 1 to {MAX_EVIDENCE_FILE_BYTES} bytes: {name}"
        )
    raw = source.read_bytes()
    if len(raw) != size:
        raise ValueError(f"evidence attachment changed while being read: {name}")
    return name, raw


def create_fit_evidence_bundle(
    study_bundle: Path,
    observations_document: object,
    evidence_files: Iterable[Path],
    output_dir: Path,
) -> dict[str, Any]:
    """Atomically retain a report and external files bound to one exact study.

    Hashing retained files establishes byte identity only. It does not establish
    who created them, whether their contents are truthful, or physical validity.
    """
    study_verification = verify_fit_study_bundle(study_bundle)
    report = evaluate_fit_study(study_bundle, observations_document)
    normalized_observations = _observations_from_report(report)
    sources = list(evidence_files)
    if not 1 <= len(sources) <= MAX_EVIDENCE_FILES:
        raise ValueError(f"fit evidence requires 1 to {MAX_EVIDENCE_FILES} attachment files")
    loaded: list[tuple[str, bytes]] = []
    names: set[str] = set()
    total_bytes = 0
    for source in sources:
        original_name, raw = _evidence_source(Path(source))
        if original_name in names:
            raise ValueError(f"evidence attachment filenames must be unique: {original_name}")
        names.add(original_name)
        total_bytes += len(raw)
        if total_bytes > MAX_EVIDENCE_TOTAL_BYTES:
            raise ValueError(f"evidence attachments exceed {MAX_EVIDENCE_TOTAL_BYTES} total bytes")
        loaded.append((original_name, raw))

    destination_input = output_dir.expanduser()
    destination = destination_input.parent.resolve() / destination_input.name
    study_root = study_bundle.expanduser().resolve()
    if destination == study_root or study_root in destination.parents:
        raise ValueError("fit-evidence output must not be created inside the immutable fit-study bundle")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"fit-evidence output directory already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        observations_text = _canonical_json(normalized_observations)
        report_text = _canonical_json(report)
        write_text_atomic(staging / "observations.json", observations_text)
        write_text_atomic(staging / "report.json", report_text)
        evidence_records: list[dict[str, Any]] = []
        for index, (original_name, raw) in enumerate(loaded, start=1):
            suffix = Path(original_name).suffix.lower()
            if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) is None:
                suffix = ".bin"
            filename = f"evidence-{index:02d}{suffix}"
            (staging / filename).write_bytes(raw)
            evidence_records.append(
                {
                    "evidence_id": f"evidence-{index:02d}",
                    "original_filename": original_name,
                    "filename": filename,
                    "bytes": len(raw),
                    "sha256": _sha256_bytes(raw),
                }
            )
        file_names = sorted(path.name for path in staging.iterdir())
        files = {
            name: {"bytes": (staging / name).stat().st_size, "sha256": _sha256_bytes((staging / name).read_bytes())}
            for name in file_names
        }
        manifest = {
            "schema_version": FIT_EVIDENCE_MANIFEST_VERSION,
            "fit_study_manifest_sha256": study_verification["manifest_sha256"],
            "fit_study_binding_sha256": study_verification["study_binding_sha256"],
            "source_project_sha256": study_verification["source_project_sha256"],
            "canonical_observations_sha256": report["canonical_observations_sha256"],
            "report_sha256": _sha256_bytes(report_text.encode("utf-8")),
            "files": files,
            "evidence": evidence_records,
            "external_evidence_attached": True,
            "evidence_authenticity_verified": False,
            "physical_fit_certified": False,
        }
        write_text_atomic(staging / "manifest.json", _canonical_json(manifest))
        publish_directory_noreplace(staging, destination)
        return {
            **manifest,
            "output_dir": str(destination),
            "manifest_sha256": _sha256_bytes((destination / "manifest.json").read_bytes()),
        }
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_fit_evidence_bundle(study_bundle: Path, evidence_bundle: Path) -> dict[str, Any]:
    """Verify every retained byte and recompute the evidence-bounded fit report."""
    study_verification = verify_fit_study_bundle(study_bundle)
    requested_root = evidence_bundle.expanduser()
    if requested_root.is_symlink():
        raise ValueError("fit-evidence bundle directory must not be a symbolic link")
    root = requested_root.resolve()
    if not root.is_dir():
        raise ValueError("fit-evidence bundle must be a regular directory")
    manifest = _exact_keys(
        _strict_json_file(root / "manifest.json"),
        {
            "schema_version", "fit_study_manifest_sha256", "fit_study_binding_sha256",
            "source_project_sha256", "canonical_observations_sha256", "report_sha256", "files",
            "evidence", "external_evidence_attached", "evidence_authenticity_verified",
            "physical_fit_certified",
        },
        "fit-evidence manifest",
    )
    if manifest["schema_version"] != FIT_EVIDENCE_MANIFEST_VERSION:
        raise ValueError("unsupported fit-evidence manifest version")
    if (
        manifest["external_evidence_attached"] is not True
        or manifest["evidence_authenticity_verified"] is not False
        or manifest["physical_fit_certified"] is not False
    ):
        raise ValueError("fit-evidence manifest contains unsupported evidence claims")
    expected_bindings = {
        "fit_study_manifest_sha256": study_verification["manifest_sha256"],
        "fit_study_binding_sha256": study_verification["study_binding_sha256"],
        "source_project_sha256": study_verification["source_project_sha256"],
    }
    if any(manifest[key] != value for key, value in expected_bindings.items()):
        raise ValueError("fit-evidence bundle is not bound to this exact fit study")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError("fit-evidence manifest files must be a non-empty object")
    actual_names = {path.name for path in root.iterdir()}
    if actual_names != set(files) | {"manifest.json"}:
        raise ValueError("fit-evidence bundle contains missing or unexpected files")
    for name, raw_record in files.items():
        record = _exact_keys(raw_record, {"bytes", "sha256"}, f"fit-evidence file {name}")
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("fit-evidence manifest contains an unsafe filename")
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"fit-evidence artifact must be a regular file: {name}")
        size = path.stat().st_size
        maximum = MAX_FIT_STUDY_FILE_BYTES if name in {"observations.json", "report.json"} else MAX_EVIDENCE_FILE_BYTES
        if size <= 0 or size > maximum:
            raise ValueError(f"fit-evidence artifact has an invalid size: {name}")
        raw = path.read_bytes()
        if (
            isinstance(record["bytes"], bool)
            or not isinstance(record["bytes"], int)
            or record["bytes"] != len(raw)
            or not isinstance(record["sha256"], str)
            or record["sha256"] != _sha256_bytes(raw)
        ):
            raise ValueError(f"fit-evidence artifact hash or size mismatch: {name}")
    evidence = manifest["evidence"]
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= MAX_EVIDENCE_FILES:
        raise ValueError("fit-evidence attachment inventory is invalid")
    evidence_names: set[str] = set()
    evidence_files_seen: set[str] = set()
    evidence_total_bytes = 0
    for index, raw_record in enumerate(evidence, start=1):
        record = _exact_keys(
            raw_record,
            {"evidence_id", "original_filename", "filename", "bytes", "sha256"},
            "fit-evidence attachment",
        )
        if record["evidence_id"] != f"evidence-{index:02d}":
            raise ValueError("fit-evidence IDs must be unique ordered strings")
        original_name = _text(record["original_filename"], "evidence original filename", maximum=255)
        filename = record["filename"]
        if original_name in evidence_names or not isinstance(filename, str) or filename in evidence_files_seen:
            raise ValueError("fit-evidence attachment names must be unique")
        evidence_names.add(original_name)
        evidence_files_seen.add(filename)
        if isinstance(record["bytes"], bool) or not isinstance(record["bytes"], int):
            raise TypeError("fit-evidence attachment byte count must be an integer")
        evidence_total_bytes += record["bytes"]
        file_record = files.get(filename)
        if not isinstance(file_record, dict) or file_record.get("bytes") != record["bytes"] or file_record.get("sha256") != record["sha256"]:
            raise ValueError(f"fit-evidence attachment does not match file inventory: {filename}")
    if evidence_total_bytes > MAX_EVIDENCE_TOTAL_BYTES:
        raise ValueError("fit-evidence attachments exceed the total byte limit")
    if set(files) != {"observations.json", "report.json", *evidence_files_seen}:
        raise ValueError("fit-evidence file inventory does not match declared attachments")
    observations = _strict_json_file(root / "observations.json")
    report = _strict_json_file(root / "report.json")
    recomputed = evaluate_fit_study(study_bundle, observations)
    if recomputed != report:
        raise ValueError("fit-evidence report does not recompute from retained observations")
    verify_fit_study_report(study_bundle, report)
    report_hash = _sha256_bytes(_bounded_bytes(root / "report.json"))
    if report_hash != manifest["report_sha256"]:
        raise ValueError("fit-evidence report hash does not match manifest")
    if report["canonical_observations_sha256"] != manifest["canonical_observations_sha256"]:
        raise ValueError("fit-evidence observations hash does not match report")
    return {
        "valid": True,
        "schema_version": FIT_EVIDENCE_MANIFEST_VERSION,
        "manifest_sha256": _sha256_bytes(_bounded_bytes(root / "manifest.json")),
        "fit_study_manifest_sha256": study_verification["manifest_sha256"],
        "evidence_file_count": len(evidence),
        "disposition": report["disposition"],
        "evidence_authenticity_verified": False,
        "physical_fit_certified": False,
    }
