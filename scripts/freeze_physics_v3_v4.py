"""Create a one-time content freeze without importing any production evaluator."""
from __future__ import annotations

import datetime
import json
import subprocess

from validate_physics_v3_v4 import CONTRACT, ROOT, digest, inventory


def main():
    paths = [CONTRACT / "PROTOCOL.md", CONTRACT / "cases.json", ROOT / "pyproject.toml",
             ROOT / "scripts/validate_physics_v3_v4.py", ROOT / "scripts/freeze_physics_v3_v4.py",
             ROOT / "tests/test_v3_validation_v4_harness.py", ROOT / ".github/workflows/physics-v3-validation-v4.yml",
             ROOT / "neurocad_cli.py", ROOT / "tests/test_beam_extrema.py", ROOT / "tests/test_composite_reference.py",
             ROOT / "research/development/shaft_biaxial_20261014/contract.json",
             ROOT / "research/development/shaft_biaxial_20261014/baseline.json",
             ROOT / "research/development/shaft_biaxial_20261014/corrected.json"]
    paths += sorted((CONTRACT / "fixtures").glob("*.json"))
    paths += sorted((ROOT / "core").rglob("*.py"))
    paths += sorted((ROOT / "core/schemas").glob("*.json"))
    data = {
        "protocol": "NC-PHYS-V3-CONFORMANCE-4",
        "frozen_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "new_case_outcomes_observed": True,
        "predecessor_outcomes_observed": True,
        "study_scope": "Known-case regression and expanded conformance, not blinded confirmation",
        "prior_source_and_unit_tests_inspected": True,
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "files": {str(p.relative_to(ROOT)): digest(p) for p in paths},
        "protected": inventory(),
        "identity_boundary": "Content hashes, not a signed or independent preregistration",
    }
    with (CONTRACT / "freeze.json").open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    print(f"Frozen {len(data['files'])} inputs and {len(data['protected'])} protected files")


if __name__ == "__main__":
    main()
