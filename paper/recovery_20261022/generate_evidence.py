"""Regenerate this manuscript's tables, figures, and source audit without experiments.

Only reads retained results. It never invokes NeuroCAD, opens a protected dataset,
or rewrites a predecessor artifact. Run from any working directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    compiler_path = "research/runs/NC-REPRO-508EC40/metrics/results.json"
    compiler = read(compiler_path)
    systems = compiler["experiments"]["NC-EXP-001"]["systems"]
    names = {
        "neurocad": "NeuroCAD",
        "nearest_neighbor_retrieval": "Nearest-neighbor retrieval",
        "normalized_dimensions_only": "Unit-normalized dimensions",
        "raw_numbers_no_unit_normalization": "Raw numbers",
        "fixed_box": "Fixed box",
    }
    if "neurocad" not in systems:
        candidates = [key for key in systems if key not in names]
        if len(candidates) != 1:
            raise ValueError(f"Cannot identify compiler arm: {list(systems)}")
        names = {candidates[0]: "NeuroCAD", **{k: v for k, v in names.items() if k != "neurocad"}}
    table = [r"\begin{tabular}{lrrrr}", r"\toprule", r"System & Train & Validation & Test & Total \\", r"\midrule"]
    summary = {}
    for key, label in names.items():
        records = systems[key]["records"]
        ids = [r["task_id"] for r in records]
        if len(records) != 240 or len(set(ids)) != 240:
            raise ValueError("Compiler records are not 240 unique task IDs")
        split_counts = {}
        for split in ("train", "val", "test"):
            rows = [r for r in records if r["split"] == split]
            if not rows and split == "val":
                rows = [r for r in records if r["split"] == "validation"]
            split_counts[split] = (sum(r["passed"] is True for r in rows), len(rows))
        if [v[1] for v in split_counts.values()] != [144, 48, 48]:
            raise ValueError(f"Unexpected splits: {split_counts}")
        total = sum(r["passed"] is True for r in records)
        summary[key] = {"label": label, "splits": split_counts, "total": [total, len(records)]}
        cells = [f"{a}/{b}" for a, b in split_counts.values()] + [f"{total}/{len(records)}"]
        table.append(label + " & " + " & ".join(cells) + r" \\")
    table.extend([r"\bottomrule", r"\end{tabular}"])
    (HERE / "compiler_table.tex").write_text("\n".join(table) + "\n", encoding="utf-8")

    v2_dir = "research/physics_v2/runs/NC-PHYS-V2-CONFIRM-001"
    raw_path = ROOT / v2_dir / "raw_results.jsonl"
    raw = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(raw) != 216 or len({r["task_id"] for r in raw}) != 216:
        raise ValueError("Physics v2 does not contain 216 unique cases")
    metrics = read(f"{v2_dir}/metrics.json")
    families = Counter(r["family"] for r in raw)
    if families != metrics["family_counts"]:
        raise ValueError("Raw and reported v2 family counts disagree")
    table = [r"\begin{tabular}{lrrr}", r"\toprule", r"Endpoint (success criterion) & Full & Hash only & Unbound \\", r"\midrule"]
    rows = [
        ("Valid request accepted", "valid", "accepted"),
        ("Geometry contradiction detected", "geometry_input_contradiction", "detected"),
        ("Material contradiction detected", "material_input_contradiction", "detected"),
        ("Load contradiction detected", "load_input_contradiction", "detected"),
        ("Stale expected hash detected", "stale_expected_hash", "detected"),
        ("Post-result geometry drift detected", "post_result_geometry_mutation", "detected"),
        ("Non-geometric edit remains current", "non_geometric_mutation", "current"),
    ]
    v2_counts = {}
    for label, family, criterion in rows:
        selected = [r for r in raw if r["family"] == family]
        counts = []
        for arm in ("full", "hash_only", "unbound"):
            if criterion == "current":
                if arm == "unbound":
                    counts.append(None)
                    continue
                if any(not isinstance(r["arms"][arm].get("current"), bool) for r in selected):
                    raise ValueError("Missing Boolean freshness result")
                count = sum(r["arms"][arm]["current"] is True for r in selected)
                expected = metrics["endpoints"][f"{arm}_non_geometric_specificity"]["successes"]
                if count != expected:
                    raise ValueError("Raw specificity and reported endpoint disagree")
            else:
                count = sum(r["arms"][arm].get(criterion) is True for r in selected)
            counts.append(count)
        v2_counts[family] = {"label": label, "total": len(selected), "counts": counts}
        cells = ["N/A" if count is None else f"{count}/{len(selected)}" for count in counts]
        table.append(label + " & " + " & ".join(cells) + r" \\")
    table.extend([r"\bottomrule", r"\end{tabular}"])
    (HERE / "physics_table.tex").write_text("\n".join(table) + "\n", encoding="utf-8")

    manifest_path = "research/runs/NC-REPRO-508EC40/manifest.json"
    manifest = read(manifest_path)
    base = ROOT / "research/runs/NC-REPRO-508EC40"
    matching, missing, mismatched = [], [], []
    for rel, expected in manifest["artifact_sha256"].items():
        item = base / rel
        if not item.is_file():
            missing.append(rel)
        elif sha(item) != expected:
            mismatched.append(rel)
        else:
            matching.append(rel)
    hosted_dir = "research/recovery_20261022/hosted-reproduction"
    hosted_metrics = read(f"{hosted_dir}/run/metrics.json")
    hosted_manifest = read(f"{hosted_dir}/run/manifest.json")
    hosted_declaration = read(f"{hosted_dir}/declaration.json")
    hosted_raw = [json.loads(line) for line in (ROOT / hosted_dir / "run/raw_results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    def outcome_projection(records):
        return {
            r["task_id"]: {
                "family": r["family"], "model": r["model"], "expected": r["expected"],
                "arms": {arm: {key: values[key] for key in ("accepted", "detected", "current", "deterministic") if key in values}
                         for arm, values in r["arms"].items()},
            }
            for r in records
        }
    if len(hosted_raw) != 216 or len({r["task_id"] for r in hosted_raw}) != 216:
        raise ValueError("Hosted repetition does not contain the 216 unique cases")
    if outcome_projection(raw) != outcome_projection(hosted_raw):
        raise ValueError("Hosted per-case outcome predicates differ from the original")
    if hosted_metrics["endpoints"] != metrics["endpoints"] or hosted_metrics["execution_errors"]:
        raise ValueError("Hosted endpoint metrics or execution errors disagree")
    if sha(ROOT / hosted_dir / "run/raw_results.jsonl") != hosted_manifest["raw_results_sha256"]:
        raise ValueError("Hosted raw artifact does not match its recorded hash")
    if sha(ROOT / hosted_dir / "run/metrics.json") != hosted_manifest["metrics_sha256"]:
        raise ValueError("Hosted metrics artifact does not match its recorded hash")
    source_paths = [compiler_path, manifest_path, f"{v2_dir}/raw_results.jsonl", f"{v2_dir}/metrics.json", f"{v2_dir}/manifest.json", "research/physics_v2/frozen/freeze.json", "research/physics_v2/CONFIRMATORY_EXECUTION.json", "TERMINAL_STATUS_2026-10-11.md", "RESEARCH_TRUTH.md"]
    source_paths += [f"{hosted_dir}/{name}" for name in ("declaration.json", "run/raw_results.jsonl", "run/metrics.json", "run/manifest.json", "CONFIRMATORY_EXECUTION.json")]
    source_paths += ["research/recovery_20261022/hosted_reproduction_audit.json"]
    audit = {
        "kind": "READ_ONLY_RETAINED_EVIDENCE_REANALYSIS",
        "runs_launched_by_generator": 0,
        "source_sha256": {p: sha(ROOT / p) for p in source_paths},
        "compiler": summary,
        "physics_v2": v2_counts,
        "physics_v2_conventional_medians": {
            arm: statistics.median(r["arms"][arm]["elapsed_ms"] for r in raw if r["arms"][arm].get("elapsed_ms") is not None)
            for arm in ("full", "hash_only", "unbound")
        },
        "physics_v2_conventional_report_size_median": statistics.median(r["arms"]["full"]["report_bytes"] for r in raw if r["arms"]["full"].get("report_bytes") is not None),
        "internal_cross_environment_reproduction": {
            "classification": hosted_declaration["classification"],
            "independent_party": hosted_declaration["independent_party"],
            "unique_cases": len(hosted_raw),
            "matching_endpoint_definitions_and_counts": len(hosted_metrics["endpoints"]),
            "all_per_case_outcome_predicates_match_original": True,
            "compared_arm_fields": ["accepted", "detected", "current", "deterministic"],
            "source_commit": hosted_declaration["source_commit"],
            "workflow_commit": hosted_declaration["workflow_commit"],
            "python": hosted_declaration["python"],
            "platform": hosted_declaration["platform"],
            "execution_errors": hosted_metrics["execution_errors"],
            "claim_boundary": "Internal repetition of known outcomes on the same 216 cases; not independent confirmation, new cases, or physical validation.",
        },
        "compiler_archive": {"listed": len(manifest["artifact_sha256"]), "matching": len(matching), "missing": missing, "mismatched": mismatched},
        "style_sha256": sha(HERE / "arxiv.sty"),
        "claim_boundary": "Retained synthetic evidence and one internal repetition; not external, physical, user, Kaggle, or new independent confirmatory evidence.",
    }
    (HERE / "evidence_sources.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "neurocad-paper-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.8), gridspec_kw={"width_ratios": [1.2, 1]})
    keys = list(names)
    labels = ["NeuroCAD", "Retrieval", "Dims. +\nunits", "Raw\nnumbers", "Fixed box"]
    x = np.arange(len(keys))
    for offset, split, color, legend in [(-0.26, "train", "#92a9b5", "Train (144)"), (0, "val", "#247d92", "Validation (48)"), (0.26, "test", "#db8a3c", "Test (48)")]:
        axes[0].bar(x + offset, [100 * summary[k]["splits"][split][0] / summary[k]["splits"][split][1] for k in keys], width=0.24, color=color, label=legend)
    axes[0].set_xticks(x, labels, fontsize=7.2)
    axes[0].set_ylim(0, 122)
    axes[0].set_yticks(range(0, 101, 20))
    axes[0].set_ylabel("Semantic exactness (%)")
    axes[0].set_title("A. Controlled compiler grammar", fontsize=9)
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=3, frameon=False, fontsize=7, handlelength=1.1, columnspacing=0.8)
    selected = ["geometry_input_contradiction", "material_input_contradiction", "load_input_contradiction", "post_result_geometry_mutation"]
    heat = [[100 * v2_counts[f]["counts"][a] / v2_counts[f]["total"] for a in range(3)] for f in selected]
    axes[1].imshow(heat, vmin=0, vmax=100, cmap="Blues", aspect="auto")
    axes[1].set_xticks([0, 1, 2], ["Full", "Hash only", "Unbound"])
    axes[1].set_yticks(range(4), ["Geometry", "Material", "Load", "Later drift"])
    axes[1].set_title("B. Physics v2 detection (%)", fontsize=9)
    for i in range(4):
        for j in range(3):
            value = heat[i][j]
            axes[1].text(j, i, f"{value:.0f}", ha="center", va="center", color="white" if value > 50 else "#152a37", fontsize=10)
    fig.tight_layout(w_pad=2.0)
    fig.savefig(HERE / "results_figure.pdf", bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(HERE / "results_figure.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"compiler": summary, "physics_v2": v2_counts, "archive": audit["compiler_archive"]}, indent=2))


if __name__ == "__main__":
    main()
