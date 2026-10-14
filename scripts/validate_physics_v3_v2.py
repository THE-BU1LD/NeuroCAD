"""Frozen v3 conformance runner; stdlib-only source mode avoids package imports."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "research/physics_v3/validation_v2"
TYPES = {
    "cantilever_beam": "CantileverBeamInput", "combined_stress": "CombinedStressInput",
    "thermal_network": "ThermalNetworkInput", "forced_vibration": "ForcedVibrationInput",
    "pipe_network": "PipeNetworkInput", "electro_thermal_wire": "ElectroThermalWireInput",
}
PROTECTED = ("research/physics_v2", "release/physics_v2", "paper")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    return {str(p.relative_to(ROOT)): digest(p) for base in PROTECTED
            for p in sorted((ROOT / base).rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def compare(actual, expected, case):
    if isinstance(expected, list):
        check(isinstance(actual, list) and len(actual) == len(expected), "array shape mismatch")
        for left, right in zip(actual, expected):
            compare(left, right, case)
    else:
        check(isinstance(actual, (float, int)) and not isinstance(actual, bool)
              and math.isfinite(actual), "non-finite or non-numeric output")
        check(abs(actual - expected) <= case["atol"] + case["rtol"] * abs(expected),
              f"actual={actual}, reference={expected}, absolute_error={abs(actual - expected)}")


def admit():
    samples = []
    for _ in range(2):
        if sys.platform == "darwin":
            raw = subprocess.check_output(["vm_stat"], text=True)
            fields = {line.split(":")[0].strip(): int(line.split(":")[1].strip().rstrip("."))
                      for line in raw.splitlines()[1:] if ":" in line}
            page = int(raw.split("page size of ")[1].split()[0])
            samples.append({"available_bytes": page * (fields["Pages free"] + fields["Pages speculative"]),
                            "pageouts": fields["Pageouts"], "swapouts": fields["Swapouts"], "raw": raw})
        elif sys.platform.startswith("linux"):
            fields = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines())
            samples.append({"available_bytes": int(fields["MemAvailable"].split()[0]) * 1024})
        else:
            return {"status": "BLOCKED", "reason": "No resource sampler for this platform"}
        time.sleep(1)
    allowed = all(s["available_bytes"] >= 512 * 1024**2 for s in samples)
    allowed = allowed and all(samples[1].get(k, 0) <= samples[0].get(k, 0) for k in ("pageouts", "swapouts"))
    disk = shutil.disk_usage(ROOT).free
    return {"status": "PASS" if allowed and disk >= 2 * 1024**3 else "BLOCKED", "samples": samples, "disk_free": disk}


class Installed:
    def __init__(self, python, output, records):
        self.python, self.output, self.records = str(python.absolute()), output, records
        self.env = dict(os.environ)
        self.env.pop("PYTHONPATH", None)
        self.env["PYTHONNOUSERSITE"] = "1"

    def call(self, arguments):
        result = subprocess.run([self.python, "-I", "-m", "neurocad_cli", *arguments],
                                cwd=self.output, env=self.env, capture_output=True, text=True, timeout=120, check=False)
        self.records.append({"arguments": arguments, "returncode": result.returncode,
                             "stdout": result.stdout, "stderr": result.stderr})
        return result

    def run(self, *arguments, code=0):
        result = self.call(list(arguments))
        check(result.returncode == code, f"Expected exit {code}, got {result.returncode}: {result.stderr}")
        return json.loads(result.stdout) if code == 0 else None


def acceptance(cli, out):
    rows = []

    def probe(name, operation):
        try:
            operation()
            rows.append({"id": name, "status": "PASS"})
        except Exception as exc:  # noqa: BLE001 -- retain every evaluation failure as evidence
            rows.append({"id": name, "status": "FAIL", "error": str(exc)})

    for source in (CONTRACT / "fixtures").glob("*.json"):
        shutil.copyfile(source, out / source.name)
    shape_names = ("hollow-shaft", "i-beam", "l-bracket", "perforated-plate")
    volumes = (math.pi * (20**2 - 12**2) * 500, (2*100*10+180*8)*1000,
               (50*5+75*5)*300, (120*80-12*math.pi*5**2)*4)
    for name, volume in zip(shape_names, volumes):
        def shape(name=name, volume=volume):
            folder = out / name
            cli.run("complex-shape", f"complex-{name}.json", "--output-dir", name)
            analysis = json.loads((folder / "analysis.json").read_text(encoding="utf-8"))
            compare(analysis["geometry"]["volume_mm3"], volume, {"atol": 1e-7, "rtol": 1e-9})
            # Preserve byte identities even for manifest structures that evolve.
            hashes = {p.name: digest(p) for p in folder.iterdir() if p.is_file()}
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            check(set(manifest["artifacts"]) == set(hashes) - {"manifest.json"}, "manifest inventory mismatch")
            for filename, entry in manifest["artifacts"].items():
                check(entry["sha256"] == hashes[filename], "manifest hash mismatch")
                check(entry["bytes"] == (folder / filename).stat().st_size, "manifest size mismatch")
            cli.run("complex-shape", f"complex-{name}.json", "--output-dir", name, code=2)
            check(hashes == {p.name: digest(p) for p in folder.iterdir() if p.is_file()}, "collision changed bundle")
            dump(out / f"{name}-bundle-hashes.json", hashes)
        probe("shape-" + name, shape)

    base = json.loads((out / "physics-v3-electrothermal-bound.json").read_text(encoding="utf-8"))
    base["context"]["geometry"]["agent_project"] = str(out / "agent-shaft-project.json")
    base["uncertainty"] = {"method": "interval", "inputs": {"current_a": {"lower": 4.5, "upper": 5.5}},
                           "outputs": ["temperature_rise_k"]}

    def request(name, value, code=0):
        dump(out / f"{name}.json", value)
        return cli.run("physics", f"{name}.json", "-o", f"{name}-report.json", code=code)

    def context():
        report = request("bound", base)
        check(report["overlay"]["spatial_field"] is False, "overlay claims spatial field")
        compare(report["bindings"]["material"]["resolved_properties"]["resistivity_ohm_m"], 1.85e-8,
                {"atol": 1e-20, "rtol": 1e-10})
        check(report["bindings"]["load_combination"]["combined_values"]["current_a"] == 5, "load combination mismatch")
        check(report["uncertainty"]["evaluation_count"] == 2, "wrong corner count")
        envelope = report["uncertainty"]["result_envelopes"]["temperature_rise_k"]
        for key, current in (("minimum", 4.5), ("maximum", 5.5)):
            compare(envelope[key], wire_reference(current), {"atol": 1e-12, "rtol": 1e-9})
        check(cli.run("physics", "--verify", "bound-report.json")["current"], "fresh report rejected")
        project = json.loads((out / "agent-shaft-project.json").read_text(encoding="utf-8"))
        project["revision"] += 1
        project["plan"]["title"] = "Metadata edit"
        dump(out / "agent-shaft-project.json", project)
        check(cli.run("physics", "--verify", "bound-report.json")["current"], "metadata falsely invalidated geometry")
        project["plan"]["components"][0]["parameters"]["radius"] = 11
        dump(out / "agent-shaft-project.json", project)
        stale = cli.call(["physics", "--verify", "bound-report.json"])
        check(stale.returncode == 2 and json.loads(stale.stdout)["status"] == "stale", "geometry edit not detected")
        pinned = copy.deepcopy(base)
        pinned["context"]["geometry"]["expected_geometry_sha256"] = report["bindings"]["geometry"]["geometry_sha256"]
        request("stale-input", pinned, 2)
    probe("bound-context-and-freshness", context)
    shutil.copyfile(CONTRACT / "fixtures/agent-shaft-project.json", out / "agent-shaft-project.json")

    for method in ("monte_carlo", "local_sensitivity"):
        def uncertainty(method=method):
            value = copy.deepcopy(base)
            value["uncertainty"]["method"] = method
            if method == "monte_carlo":
                value["uncertainty"].update(samples=32, seed=20261014)
            first = request(method, value)["uncertainty"]
            second = request(method + "-repeat", value)["uncertainty"]
            check(first == second, "uncertainty not reproducible")
            if method == "monte_carlo":
                rng = random.Random(20261014)
                values = [wire_reference(rng.uniform(4.5, 5.5)) for _ in range(32)]
                actual = first["result_statistics"]["temperature_rise_k"]
                for key, expected in (("mean", statistics.fmean(values)), ("minimum", min(values)),
                                      ("maximum", max(values)), ("sample_standard_deviation", statistics.stdev(values))):
                    compare(actual[key], expected, {"atol": 1e-12, "rtol": 1e-9})
            else:
                resistance = 1.85e-8 * 0.1 / (math.pi * 100 * 1e-6)
                expected = 4 * resistance * 5 / (1 - 2 * resistance * 0.004 * 25)**2
                actual = first["local_derivatives"]["current_a"]["derivatives"]["temperature_rise_k"]
                compare(actual, expected, {"atol": 1e-12, "rtol": 1e-7})
        probe(method, uncertainty)

    changes = {
        "geometry-contradiction": lambda x: x["inputs"].update(length_mm=101),
        "material-contradiction": lambda x: x["inputs"].update(resistivity_ohm_m=2e-8),
        "load-contradiction": lambda x: x["inputs"].update(current_a=6),
        "extrapolation": lambda x: x["context"]["material"].update(evaluation_temperature_k=500),
        "mixed-coordinates": lambda x: x["context"]["load_cases"][0].update(coordinate_system="world"),
        "wrong-units": lambda x: x["inputs"].update(length_mm="100 m"),
    }
    for name, change in changes.items():
        def reject(name=name, change=change):
            value = copy.deepcopy(base)
            change(value)
            request(name, value, 2)
            check(not (out / f"{name}-report.json").exists(), "rejected request published report")
        probe(name, reject)

    for name, changes in (("invalid-shaft", {"inner_diameter_mm": 45}),):
        def bad_shape(name=name, changes=changes):
            value = json.loads((out / "complex-hollow-shaft.json").read_text(encoding="utf-8"))
            value["parameters"].update(changes)
            dump(out / f"{name}.json", value)
            cli.run("complex-shape", f"{name}.json", "--output-dir", name, code=2)
            check(not (out / name).exists(), "invalid shape published")
        probe(name, bad_shape)
    def plate_load():
        value = json.loads((out / "complex-perforated-plate.json").read_text(encoding="utf-8"))
        value["analysis"]["axial_force_n"] = 1
        dump(out / "loaded-plate.json", value)
        cli.run("complex-shape", "loaded-plate.json", "--output-dir", "loaded-plate", code=2)
        check(not (out / "loaded-plate").exists(), "unsupported plate published")
    probe("unsupported-plate-load", plate_load)
    return rows


def wire_reference(current):
    """Independent SI heat balance for the frozen bound-wire fixture."""
    resistance = 1.85e-8 * 0.1 / (math.pi * 100 * 1e-6)
    return current**2 * resistance / (0.5 - current**2 * resistance * 0.004)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--installed-python", type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "RUNNING", "mode": "INSTALLED" if args.installed_python else "SOURCE_SCALAR",
               "started_at_unix": time.time(), "python": sys.version, "platform": platform.platform(), "cases": [], "commands": [],
               "physical_validation": "NOT_STARTED", "independent_reproduction": "NOT_STARTED"}
    lock = ROOT / "research/physics_v3/.validation.lock"
    owned = False
    try:
        with lock.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        owned = True
        freeze = json.loads((CONTRACT / "freeze.json").read_text(encoding="utf-8"))
        receipt["freeze_sha256"] = digest(CONTRACT / "freeze.json")
        receipt["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        receipt["git_status"] = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
        for name, expected in freeze["files"].items():
            check(digest(ROOT / name) == expected, f"Frozen content changed: {name}")
        check(inventory() == freeze["protected"], "Protected inventory changed before run")
        cases = json.loads((CONTRACT / "cases.json").read_text(encoding="utf-8"))
        check({c["model"] for c in cases} == set(TYPES), "Model coverage changed")
        check(len({c["id"] for c in cases}) == len(cases), "Duplicate case ID")
        cli = None
        if args.installed_python:
            check(not out.is_relative_to(ROOT), "Installed working directory must be outside checkout")
            receipt["admission"] = admit()
            if receipt["admission"]["status"] != "PASS":
                receipt["status"] = "BLOCKED"
                return 3
            cli = Installed(args.installed_python, out, receipt["commands"])
            code = ("import core.physics_advanced as m, neurocad_cli as c, hashlib,json,importlib.metadata as d; "
                    "print(json.dumps({'module':m.__file__,'cli':c.__file__,'sha256':hashlib.sha256(open(m.__file__,'rb').read()).hexdigest(),"
                    "'version':d.version('neurocad-research')}))")
            identity = subprocess.run([cli.python, "-I", "-c", code], cwd=out, env=cli.env,
                                      capture_output=True, text=True, timeout=120, check=False)
            check(identity.returncode == 0, identity.stderr)
            receipt["installed_identity"] = json.loads(identity.stdout)
            check(all(not Path(receipt["installed_identity"][key]).resolve().is_relative_to(ROOT) for key in ("module", "cli")),
                  "Installed modules resolve into checkout")
            check(receipt["installed_identity"]["sha256"] == freeze["files"]["core/physics_advanced.py"], "Installed source mismatch")
            site = Path(receipt["installed_identity"]["module"]).parent.parent
            installed_hashes = {}
            for name, expected in freeze["files"].items():
                if name.startswith("core/") or name == "neurocad_cli.py":
                    installed_hashes[name] = digest(site / name)
                    check(installed_hashes[name] == expected, f"Installed source mismatch: {name}")
            receipt["installed_source_hashes"] = installed_hashes
        else:
            spec = importlib.util.spec_from_file_location("v3_scalar_subject", ROOT / "core/physics_advanced.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        for case in cases:
            row = {"id": case["id"], "model": case["model"], "status": "FAIL", "expected": case["expected"]}
            try:
                if cli:
                    request = out / (case["id"] + ".json")
                    dump(request, {"model": case["model"], "inputs": case["inputs"]})
                    response = cli.call(["physics", str(request)])
                    if case["error"]:
                        check(response.returncode == 2 and case["error"] in response.stderr, "Wrong rejection diagnostic/status")
                        row["rejection"] = response.stderr
                        row["status"] = "PASS"
                        receipt["cases"].append(row)
                        continue
                    check(response.returncode == 0, response.stderr)
                    report = json.loads(response.stdout)
                else:
                    try:
                        report = getattr(module, case["model"])(getattr(module, TYPES[case["model"]])(**case["inputs"]))
                    except (ValueError, TypeError) as exc:
                        check(case["error"] is not None and case["error"] in str(exc), f"Unexpected rejection: {exc}")
                        row.update(status="PASS", rejection=str(exc))
                        receipt["cases"].append(row)
                        continue
                check(case["error"] is None, "Invalid input accepted")
                row["report"] = report
                errors = []
                for key, expected in case["expected"].items():
                    actual = report["results"]
                    try:
                        for part in key.split("."):
                            actual = actual[part]
                        compare(actual, expected, case)
                    except Exception as exc:  # noqa: BLE001 -- retain every evaluation failure as evidence
                        errors.append({"field": key, "error": str(exc)})
                row["mismatches"] = errors
                check(not errors, "Reference mismatch")
                row["status"] = "PASS"
            except Exception as exc:  # noqa: BLE001 -- retain every evaluation failure as evidence
                row["error"] = str(exc)
            receipt["cases"].append(row)
            dump(out / "receipt.json", receipt)
        if cli:
            receipt["acceptance"] = acceptance(cli, out)
        all_rows = receipt["cases"] + receipt.get("acceptance", [])
        receipt["passed"] = sum(r["status"] == "PASS" for r in all_rows)
        receipt["total"] = len(all_rows)
        receipt["status"] = "PASS" if receipt["passed"] == receipt["total"] else "FAIL"
    except Exception as exc:  # noqa: BLE001 -- retain every evaluation failure as evidence
        receipt.update(status="INVALID", error=str(exc))
    finally:
        if owned:
            receipt["protected_unchanged"] = inventory() == json.loads((CONTRACT / "freeze.json").read_text(encoding="utf-8"))["protected"]
            if not receipt["protected_unchanged"]:
                receipt["status"] = "INVALID"
            lock.unlink()
        dump(out / "receipt.json", receipt)
        print(json.dumps({k: receipt[k] for k in ("status", "mode", "passed", "total") if k in receipt}))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
