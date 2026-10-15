"""Paired local timing of old supported clauses; new capabilities reported separately."""
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import sys
import time

from core import conversational_parser as candidate
from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.project import EnclosureProject

folder = Path(__file__).resolve().parent
base_file = folder / "base_conversational_parser.py.txt"
loader = importlib.machinery.SourceFileLoader("core.quantity_baseline", str(base_file))
spec = importlib.util.spec_from_loader(loader.name, loader)
base = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = base
loader.exec_module(base)
project = EnclosureProject("quantity-timing", EnclosureSpec(
    outer_size_mm=(80, 60, 30), wall_mm=2, floor_mm=2, profile="fdm_standard",
    lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
    cutouts=(CutoutSpec("power", "circular", "front", (0, 10), diameter_mm=4),),
))
plan = json.loads((folder / "fixture-recovery-and-efficiency-addendum.json").read_text())["benchmark_plan"]
inputs = plan["inputs"]
modules = {"base": base, "candidate": candidate}
parity = []
for source in inputs:
    results = [module.parse_conversation(source, project) for module in modules.values()]
    old, new = results
    parity.append({"source": source, "base_status": old.status, "candidate_status": new.status,
                   "same_candidate": (old.candidate.to_dict() if old.candidate else None) == (new.candidate.to_dict() if new.candidate else None),
                   "same_preserve": old.preserve == new.preserve, "same_baseline_hash": old.baseline_sha256 == new.baseline_sha256})
assert all(row["same_candidate"] and row["same_preserve"] and row["same_baseline_hash"] for row in parity[:5]), parity
rows = []
for round_number in range(plan["rounds"]):
    order = ["base", "candidate"] if round_number % 2 == 0 else ["candidate", "base"]
    for label in order:
        parse = modules[label].parse_conversation
        for index, source in enumerate(inputs):
            start = time.perf_counter_ns()
            for _ in range(plan["repetitions_per_input_per_round"]):
                parse(source, project)
            elapsed = time.perf_counter_ns() - start
            rows.append({"round": round_number, "implementation": label, "input_index": index,
                         "nanoseconds_per_request": elapsed / plan["repetitions_per_input_per_round"]})
medians = {}
for label in modules:
    per_round = [sum(row["nanoseconds_per_request"] for row in rows if row["implementation"] == label and row["round"] == r and row["input_index"] < 5) / 5 for r in range(plan["rounds"])]
    medians[label] = {"per_round_mean_ns": per_round, "median_ns": statistics.median(per_round)}
result = {"scope": "Same-host warm local engineering microbenchmark, five old supported clauses. No CAD/native/model or production throughput inference.",
          "plan": plan, "python": sys.version, "platform": platform.platform(), "parity": parity,
          "rows": rows, "old_supported_aggregate": medians,
          "latency_reduction_percent": 100 * (1 - medians["candidate"]["median_ns"] / medians["base"]["median_ns"]),
          "base_parser_sha256": hashlib.sha256(base_file.read_bytes()).hexdigest(),
          "candidate_source_hashes": {name: hashlib.sha256(Path("core", name).read_bytes()).hexdigest() for name in ("conversational_parser.py", "conversation_quantities.py")}}
with (folder / "timings.json").open("x") as output:
    json.dump(result, output, indent=2)
    output.write("\n")
print(json.dumps({key: value for key, value in result.items() if key not in {"rows", "plan", "parity"}}, indent=2))
