"""Exercise an installed CLI outside the checkout and retain acceptance evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess  # Fixed argument vectors to an explicitly selected local CLI.  # nosec B404
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--require-stl", action="store_true")
    args = parser.parse_args()
    executable = args.executable.absolute()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    records: list[dict] = []
    receipt = {"status": "RUNNING", "executable": str(executable),
               "require_stl": args.require_stl, "commands": records,
               "independent_validation": False}

    def run(*command: str, expected: int = 0) -> str:
        result = subprocess.run([str(executable), *command], cwd=root, env=env,  # nosec B603
                                capture_output=True, text=True, timeout=180, check=False)
        records.append({"arguments": command, "returncode": result.returncode,
                        "expected_returncode": expected, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != expected:
            raise RuntimeError(f"Unexpected exit status for {command}: {result.stderr}")
        return result.stdout

    try:
        run("--version")
        run("doctor")
        prompt = ("80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
                  "friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; "
                  "rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C")
        run("enclosure", "interpret", prompt, "--project-id", "install-check", "--project-output", "r1.json")
        original = (root / "r1.json").read_bytes()
        run("enclosure", "edit", "r1.json", "--instruction", "set wall thickness to 2.4 mm", "--output", "r2.json")
        before = json.loads(original)
        after = json.loads((root / "r2.json").read_bytes())
        expected_spec = dict(before["spec"], wall_mm=2.4)
        if after["spec"] != expected_spec or after["revision"] != before["revision"] + 1:
            raise RuntimeError("Edit changed unrelated specification fields or revision")
        run("enclosure", "edit", "r2.json", "--instruction", "set wall thickness to 100 mm", "--output", "invalid.json", expected=2)
        if (root / "invalid.json").exists():
            raise RuntimeError("Rejected edit published an output")
        run("enclosure", "edit", "r2.json", "--instruction", "set wall thickness to 2.6 mm", "--output", "r1.json", expected=2)
        if (root / "r1.json").read_bytes() != original:
            raise RuntimeError("Original revision was overwritten")
        run("enclosure", "preflight", "r2.json")
        stl = ("--stl",) if args.require_stl else ()
        run("enclosure", "build", "r2.json", "--output-dir", "bundle", *stl)
        verify = ("enclosure", "verify", "bundle", "--project", "r2.json")
        report = json.loads(run(*verify, *(("--require-stl",) if args.require_stl else ())))
        if report["checks"]["expected_project_matches"] is not True:
            raise RuntimeError("Expected revision was not checked")
        run("enclosure", "verify", "bundle", "--project", "r1.json", expected=2)
        if not args.require_stl:
            run(*verify, "--require-stl", expected=2)
        run("enclosure", "build", "r2.json", "--output-dir", "bundle", expected=2)
        # Keep the good bundle intact; inject and remove one inventory violation.
        extra = root / "bundle" / "untracked.txt"
        extra.write_text("tamper probe\n", encoding="utf-8")
        run(*verify, expected=2)
        extra.unlink()
        run(*verify)
        receipt["project_sha256"] = hashlib.sha256((root / "r2.json").read_bytes()).hexdigest()
        receipt["status"] = "PASS"
    except Exception as exc:
        receipt["status"] = "FAIL"
        receipt["error"] = str(exc)
        raise
    finally:
        (root / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
