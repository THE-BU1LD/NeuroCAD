"""Render and hash the matched VeriCodeGen prompt bundle before Stage 2 execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.json_io import strict_json_loads

BUNDLE_VERSION = "vericodegen-prompt-bundle-v1"
ARMS = ("direct", "structured")


class PromptBundleError(ValueError):
    """Raised when the frozen prompt bundle is incomplete or asymmetric."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_bundle(path: str | Path) -> dict[str, Any]:
    value = strict_json_loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PromptBundleError("prompt bundle root must be an object")
    return value


def validate_bundle(bundle: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {"bundle_version", "scientific_evidence", "shared_rules", "direct", "structured"}
    unknown = sorted(set(bundle) - allowed)
    if unknown:
        errors.append(f"unsupported bundle keys: {', '.join(unknown)}")
    if bundle.get("bundle_version") != BUNDLE_VERSION:
        errors.append(f"bundle_version must equal {BUNDLE_VERSION}")
    if bundle.get("scientific_evidence") is not False:
        errors.append("scientific_evidence must remain false before outcomes")

    shared = bundle.get("shared_rules")
    if not isinstance(shared, list) or len(shared) < 3:
        errors.append("shared_rules must contain at least three rules")
        shared = []
    else:
        if any(not isinstance(rule, str) or not rule.strip() for rule in shared):
            errors.append("every shared rule must be a non-empty string")
        normalized = [rule.strip() for rule in shared if isinstance(rule, str)]
        if len(normalized) != len(set(normalized)):
            errors.append("shared_rules must not contain duplicates")

    for arm in ARMS:
        config = bundle.get(arm)
        if not isinstance(config, Mapping):
            errors.append(f"{arm} must be an object")
            continue
        contract = config.get("output_contract")
        if not isinstance(contract, list) or not contract:
            errors.append(f"{arm}.output_contract must be a non-empty list")
        elif any(not isinstance(rule, str) or not rule.strip() for rule in contract):
            errors.append(f"every {arm}.output_contract rule must be non-empty")

    direct = bundle.get("direct")
    if isinstance(direct, Mapping):
        unknown = sorted(set(direct) - {"output_contract"})
        if unknown:
            errors.append(f"direct has unsupported keys: {', '.join(unknown)}")

    structured = bundle.get("structured")
    if isinstance(structured, Mapping):
        unknown = sorted(set(structured) - {"output_contract", "schema_path", "spec_version"})
        if unknown:
            errors.append(f"structured has unsupported keys: {', '.join(unknown)}")
        if not isinstance(structured.get("schema_path"), str) or not structured.get("schema_path", "").strip():
            errors.append("structured.schema_path must be non-empty")
        if structured.get("spec_version") != "vericodegen-structured-v1":
            errors.append("structured.spec_version must equal vericodegen-structured-v1")

    return errors


def render_prompt(bundle: Mapping[str, Any], arm: str) -> str:
    if arm not in ARMS:
        raise PromptBundleError(f"arm must be one of {', '.join(ARMS)}")
    errors = validate_bundle(bundle)
    if errors:
        raise PromptBundleError("prompt bundle invalid:\n- " + "\n- ".join(errors))

    lines = [
        "VERICODEGEN SUCCESSOR STUDY — FROZEN SYSTEM TEMPLATE",
        "",
        "SHARED TASK RULES",
    ]
    lines.extend(f"{index}. {rule.strip()}" for index, rule in enumerate(bundle["shared_rules"], 1))
    lines.extend(["", f"OUTPUT CONTRACT — {arm.upper()}"])
    lines.extend(
        f"{index}. {rule.strip()}"
        for index, rule in enumerate(bundle[arm]["output_contract"], 1)
    )
    if arm == "structured":
        lines.extend(
            [
                "",
                f"Structured schema: {bundle['structured']['schema_path']}",
                f"Required spec_version: {bundle['structured']['spec_version']}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def shared_block(bundle: Mapping[str, Any]) -> str:
    errors = validate_bundle(bundle)
    if errors:
        raise PromptBundleError("prompt bundle invalid:\n- " + "\n- ".join(errors))
    return "\n".join(rule.strip() for rule in bundle["shared_rules"]) + "\n"


def build_receipt(bundle: Mapping[str, Any], *, schema_bytes: bytes) -> dict[str, Any]:
    errors = validate_bundle(bundle)
    if errors:
        raise PromptBundleError("prompt bundle invalid:\n- " + "\n- ".join(errors))
    direct = render_prompt(bundle, "direct").encode("utf-8")
    structured = render_prompt(bundle, "structured").encode("utf-8")
    shared = shared_block(bundle).encode("utf-8")
    return {
        "receipt_version": "vericodegen-prompt-receipt-v1",
        "bundle_version": bundle["bundle_version"],
        "scientific_evidence": False,
        "shared_sha256": _sha256_bytes(shared),
        "direct_sha256": _sha256_bytes(direct),
        "structured_sha256": _sha256_bytes(structured),
        "structured_schema_sha256": _sha256_bytes(schema_bytes),
        "direct_bytes": len(direct),
        "structured_bytes": len(structured),
        "prompt_byte_delta": len(structured) - len(direct),
        "shared_rule_count": len(bundle["shared_rules"]),
        "direct_contract_rule_count": len(bundle["direct"]["output_contract"]),
        "structured_contract_rule_count": len(bundle["structured"]["output_contract"]),
        "frozen": True,
        "outcomes_observed": False,
    }


def freeze_prompt_bundle(
    bundle_path: str | Path,
    *,
    repository_root: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    bundle = load_bundle(bundle_path)
    errors = validate_bundle(bundle)
    if errors:
        raise PromptBundleError("prompt bundle invalid:\n- " + "\n- ".join(errors))

    root = Path(repository_root)
    schema_path = root / bundle["structured"]["schema_path"]
    if not schema_path.is_file():
        raise PromptBundleError(f"structured schema not found: {schema_path}")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    direct_text = render_prompt(bundle, "direct")
    structured_text = render_prompt(bundle, "structured")
    (output / "direct_system_v1.txt").write_text(direct_text, encoding="utf-8")
    (output / "structured_system_v1.txt").write_text(structured_text, encoding="utf-8")

    receipt = build_receipt(bundle, schema_bytes=schema_path.read_bytes())
    (output / "prompt_receipt_v1.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = freeze_prompt_bundle(
        args.bundle,
        repository_root=args.repository_root,
        output_dir=args.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
