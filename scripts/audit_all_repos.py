#!/usr/bin/env python3
"""Generate per-repository research audit checklists for the local portfolio."""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

NEUROCAD_ROOT = Path(__file__).resolve().parents[1]
ROOT = NEUROCAD_ROOT.parent
AUDIT_DATE = datetime.now(timezone.utc).date().isoformat()
OUT = NEUROCAD_ROOT / "audits" / f"all-repos-{AUDIT_DATE}"
PRIOR = ROOT / "RESEARCH_REPOSITORY_AUDIT_2026-09-12.md"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".cache",
    ".agent-mypy-cache",
    ".agent-mypy-tools",
    ".deepwork-orchestrator",
    "SourceZips",
    "results",
    "runs",
    "outputs",
    "artifacts",
    "checkpoints",
    "wandb",
    "pytest-of-ryan",
    "data",
    "datasets",
    "archive",
    "archives",
    "logs",
    "log",
    "models",
    "weights",
    "submission",
    "submission_package",
    ".local-recovery",
    ".tmp-release-venv",
    ".tmp-release-work",
    ".portal-canonical",
    ".provenance",
}

MAX_FILES_PER_REPO = 1200
MAX_WALK_DEPTH = 6

TEXT_EXTS = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".sh",
    ".tex",
    ".rst",
    ".cfg",
    ".ini",
}

MARKERS = {
    "todo": re.compile(r"\b(TODO|FIXME|TBD|XXX)\b", re.IGNORECASE),
    "placeholder": re.compile(r"\b(placeholder|replace_with|your[-_ ]|example\.com|dummy|mock|fake)\b", re.IGNORECASE),
    "stub": re.compile(r"\b(stub|scaffold|not implemented|NotImplementedError|pass\s*(#|$)|\.\.\.)\b", re.IGNORECASE),
    "hardcoded": re.compile(r"\b(hardcoded|hard-coded|shortcut|toy|synthetic only)\b", re.IGNORECASE),
    "claim": re.compile(r"\b(state[- ]of[- ]the[- ]art|SOTA|novel|breakthrough|conference|publication|paper-ready)\b", re.IGNORECASE),
}

NON_ACTIONABLE_MARKER_CONTEXT = [
    re.compile(
        r"\b(no|not|without|forbid|forbidden|prevents?|rejects?|avoid|do not|must not|cannot|unsupported|invalid|quarantine|demote|boundary)\b"
        r".{0,120}\b(marker|placeholder|stub|mock|fake|publication|conference|paper-ready|implemented|claim|evidence)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(assert|assertion|forbidden|integrity|audit|truth|status|boundary|classification|claim boundary|invalid claims|valid claims|checklist)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnot (a |an )?(validated|complete|publication-ready|paper-ready)\b", re.IGNORECASE),
    re.compile(r"\bplaceholder scan\b", re.IGNORECASE),
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\bunittest\.mock\b|\bfrom unittest import mock\b|\bfrom unittest\.mock\b", re.IGNORECASE),
    re.compile(r"\bexample\.com\b", re.IGNORECASE),
]

GENERIC_FINDING_SUPPRESS_CLASSES = {"unused/dead"}

FOCUSED_NOTES = {
    "NGMT": [
        "`RESEARCH_TRUTH.md` reports Recovery v2 over 60 cells with primary bounded NGMT-minus-original delta `+0.0033429166`, 95% CI `[-0.0020387918, 0.0100040585]`, sign-flip `p=0.4375`; this fails the improvement gate.",
        "`FINAL_SUBMISSION_STATUS.md` is explicitly `EXPERIMENT PACKAGE INCOMPLETE`; six quick/full protocol cells collide and source/paper/script hashes do not match the current artifacts.",
        "Six old mechanism seed-101 cells have 156 rather than 336 targets; keep them as compromised history, not publication evidence.",
        "Next fix: rerun the publication/provenance gate after license/authorship decisions and rebuild source/paper artifacts from the current tree without reusing collided IDs.",
    ],
    "ML4SematicIntelligence": [
        "`PROJECT_TRUTH.md` classifies 64 hypotheses as 2 project-specific external implementations, 14 shared diagnostics, and 48 specification-only entries; a claim of 64 implemented projects is false.",
        "ML4SEMAN-033 COGS artifacts are verified but mixed/development-informed. GRU exact-match generalization is 0.000 and structural diagnostics are nonzero, so it is negative/error-analysis evidence, not a success claim.",
        "`TRUTH_MAP.md` blocks any main-conference paper claim until there is a clean holdout, stronger baseline, independent replication, and human/venue review.",
        "Next fix: narrow active scope to ML4SEMAN-033/059 and freeze the 48 spec-only entries out of implementation counts.",
    ],
    "EPU": [
        "Unit verification passed with `python3 -m unittest discover -s tests -v` (3 tests).",
        "`results/full_digits.json` is a real digits benchmark, but full iterative retrieval is about 0.0956 accuracy while direct nearest-prototype/single-step controls are much stronger; this is evidence against the full iterative mechanism.",
        "RTL is illustrative and is not verified equivalent to the Python reference.",
        "Fixed in this pass: added `requirements.txt`. Next fix: repair the dynamics or label the full iterative EPU as a failed ablation.",
    ],
    "DRPT": [
        "Unit verification passed with `python3 -m unittest discover -s tests -v` (6 tests).",
        "`src/train.py` and `src/eval.py` feed `prev_onehot`; tests verify that the previous phase changes the controller path.",
        "`runs/drpt_smoke/history.json` records finite losses and no NaNs in the smoke run.",
        "Next fix: add a paired no-feedback ablation across multiple seeds before claiming a hysteresis/phase-memory advantage.",
    ],
    "RIS": [
        "Unit verification passed with `python3 -m unittest discover -s tests -v` (3 tests).",
        "README now removes the old IRR claim; retained results cover Wisconsin Diagnostic Breast Cancer with 3 seeds.",
        "Current evidence: adaptive `1e-4` and fixed `1e-4` are essentially tied, while fixed `1e-6` is much worse.",
        "Next fix: keep the bounded Hessian-estimation claim unless a second dataset/objective and stronger numerical baselines are added.",
    ],
}

PRIOR_VERDICTS = {
    "Adaptive-Theory-Geometry": "Evidence-bounded negative/mixed: geometry recovery works in bounded settings, but ATG blend/selector added value is falsified.",
    "Assumption-Integrity": "Evidence-partial with adverse natural result: guarded synthetic paths exist, but Adult natural benchmark favors the unconditioned model.",
    "BU1LDLanding": "Product/portfolio landing site, not scientific evidence.",
    "CDW": "Implementation-rich with mixed/negative evidence; not a blanket-success monorepo.",
    "Causal-Memory-Use": "Strong diagnostic package, but exchangeability failures weaken naive causal interpretation.",
    "ColorWorld": "Engineering prototype with synthetic/demo evidence; no production-trained visual-quality evidence.",
    "DRPT": "Partial runnable prototype: train/eval now exercise previous-phase conditioning, smoke losses are finite, and unit tests pass; no matched no-feedback ablation, external baseline, multi-seed study, or validated hysteresis effect exists.",
    "EPU": "Partial real-data prototype: Python reference tests pass and a digits retrieval benchmark exists, but full iterative retrieval underperforms nearest-prototype/single-step controls and RTL/hardware equivalence remains unverified.",
    "Eigen-JEPA": "Real implementation with null/partial real-panel evidence after multiplicity correction.",
    "EigenFinance": "Empty shell: license only in the prior audit.",
    "FI-JEPA": "Evidence-partial negative: FI-JEPA underperforms raw-context ridge/persistence on retained evidence.",
    "FIM": "Evidence-bounded negative maintained study; no natural-domain or SOTA advantage shown.",
    "Fabric-Induced-Memory": "Legacy divergent FIM fork; not independent replication.",
    "Finance-Meta-Research-LGWM-Hedge-Fund-864431cb2c398254eb81322d15f12ac9eaa22a0a": "Empty shell: license only in the prior audit.",
    "Finance-Meta-Research-org-infra-da0cd622742f1b6b0d07ec6e8c785cf98ed8f977": "Infrastructure stub, not research implementation.",
    "FinanceMeta-Landing": "Product/portfolio site, not a research repo.",
    "GaussianMemory": "Research-complete negative study: no corrected contrast survives and memory write/read gradient path is absent.",
    "IRIS-Draft": "Archival negative result; canonical raw trajectories unavailable locally.",
    "IY-ERN": "React landing page with unreplaced integration placeholder, not scientific evidence.",
    "LAM-JEPA": "Research-complete negative for frozen ARC hypothesis; successor protocol still has TBD thresholds.",
    "MIT-Stanford-Princeton-Research": "Portfolio screening system, not 64 completed papers.",
    "ML4Industry": "Mixed portfolio: many shared scaffolds; only a small subset has external evidence.",
    "ML4Science": "Audited negative/inconclusive portfolio; external proposals fail.",
    "ML4SematicIntelligence": "Partial evidence-indexed portfolio: 2 project-specific external implementations, 14 shared diagnostics, and 48 specification-only entries; zero conference-ready papers or defensible positive scientific claims.",
    "MLInvention": "Good foundry engineering, but promoted deeper results are negative/inconclusive.",
    "NGMT": "Evidence-partial negative: current Recovery v2 result fails the primary improvement gate; submission package remains incomplete because historical cells and provenance do not match current source/paper artifacts.",
    "NPMS": "Strong controlled diagnostic, but external/public benchmark validation incomplete.",
    "NeuroCAD": "Engineering-verified compiler with partial research evidence; benchmark is bounded to its own grammar.",
    "Olympus": "Strong software platform, scientific scaffold: role families remain smoke-not-promoted.",
    "PercyxLyla": "Software/control-plane project, not a scientific contribution by project count.",
    "PercyxLyla-all-in": "Duplicate/branch snapshot; not independent science.",
    "PercyxLyla-complete-os": "Duplicate/branch snapshot; not independent science.",
    "Project-2424": "Control plane/foundry; only a small subset is implemented research and zero paper-ready/reproduced.",
    "QFIM": "Legacy FIM snapshot with weaker evidence hygiene; not a separate confirmation.",
    "RIS": "Partial bounded numerical benchmark: the unsupported IRR claim has been removed; current code/tests/results cover coordinate-adaptive finite-difference Hessian estimation on Wisconsin Diagnostic Breast Cancer only.",
    "Research-Pilot": "Workflow web prototype with template markers and checked-in environment risk.",
    "Residual-Event-Tokenization": "Executable prototype without retained scientific evidence or tests.",
    "SCDMIT": "Implementation-rich but negative/insufficient retained evidence.",
    "Saphir-Whoof": "Experiment-ready implementation with unverified real-model evidence.",
    "SourceZips": "Archive store, not an independent repository.",
    "Speechly": "Functional demo/scaffold; heuristics and random/untrained layers are not validated research.",
    "THE-BU1LD-APEN-Synthica-c7a19f075eced3bbcb86fd6d881cf0e57b7436ae": "Evidence-partial negative APEN plus Synthica foundry with no submission-ready packages.",
    "VertexED": "Education product repository; research evidence must remain isolated from product claims.",
    "results": "Output directory, not an independent repository.",
}


@dataclass
class Finding:
    severity: str
    component: str
    problem: str
    evidence: str
    impact: str
    fix: str


def is_text(path: Path) -> bool:
    return path.suffix in TEXT_EXTS


def safe_slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")


def iter_files(repo: Path):
    yielded = 0
    for dirpath, dirnames, filenames in os.walk(repo):
        current = Path(dirpath)
        try:
            current.relative_to(OUT)
            dirnames[:] = []
            continue
        except ValueError:
            pass
        rel_depth = len(Path(dirpath).relative_to(repo).parts)
        if rel_depth >= MAX_WALK_DEPTH:
            dirnames[:] = []
        else:
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                if path.is_file():
                    yielded += 1
                    if yielded > MAX_FILES_PER_REPO:
                        return
                    yield path
            except OSError:
                continue


def read_excerpt(path: Path, limit: int = 2400) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def is_actionable_marker_line(line: str) -> bool:
    """Return false for deliberate truth-boundary/audit/test text.

    The audit still records unresolved implementation placeholders, but it no
    longer penalizes docs that explicitly say a repo is *not* publication-ready
    or tests that forbid placeholder/fake claims.
    """

    return not any(pattern.search(line) for pattern in NON_ACTIONABLE_MARKER_CONTEXT)


def classify_repo(name: str, has_git: bool, files: list[Path], marker_counts: Counter[str]) -> str:
    verdict = PRIOR_VERDICTS.get(name, "").lower()
    file_names = {p.name for p in files}
    has_code = any(p.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".cpp", ".c"} for p in files)
    has_tests = any("test" in str(p.relative_to(p.parents[len(p.parents) - 1])).lower() for p in files)
    if "empty shell" in verdict or (not has_code and len(files) <= 3):
        return "placeholder/stub/mock"
    if "archive store" in verdict or "output directory" in verdict or "duplicate" in verdict or "legacy" in verdict:
        return "unused/dead"
    if verdict.startswith("partial") or any(token in verdict for token in ("evidence-partial", "evidence-bounded", "real implementation", "research-complete", "strong diagnostic", "engineering prototype", "implementation-rich")):
        return "partial"
    if re.search(r"\b(broken|nan)\b", verdict) and "not broken" not in verdict:
        return "broken"
    if "toy/scaffold" in verdict or "literal scaffold" in verdict or "specification-only" in verdict or "not a scientific evidence" in verdict:
        return "scaffold"
    if "landing" in verdict or "product" in verdict:
        return "scaffold"
    if not has_tests and has_code:
        return "untested"
    if has_code and has_git and ("pyproject.toml" in file_names or "package.json" in file_names):
        return "partial"
    if has_code:
        return "partial"
    if marker_counts["placeholder"] or marker_counts["stub"]:
        return "placeholder/stub/mock"
    return "partial"


def scan_repo(repo: Path) -> tuple[list[Path], Counter[str], dict[str, list[str]], Counter[str]]:
    files = list(iter_files(repo))
    ext_counts = Counter(p.suffix or "<none>" for p in files)
    marker_counts: Counter[str] = Counter()
    marker_examples: dict[str, list[str]] = {k: [] for k in MARKERS}
    for path in files:
        if not is_text(path):
            continue
        text = read_excerpt(path, 12000)
        rel = str(path.relative_to(repo))
        for marker, regex in MARKERS.items():
            actionable_matches: list[re.Match[str]] = []
            actionable_samples: list[tuple[int, str]] = []
            for match in regex.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                sample = text.splitlines()[line_no - 1].strip()
                if is_actionable_marker_line(sample):
                    actionable_matches.append(match)
                    actionable_samples.append((line_no, sample))
            if actionable_matches:
                marker_counts[marker] += len(actionable_matches)
                if len(marker_examples[marker]) < 6:
                    line_no, sample = actionable_samples[0]
                    marker_examples[marker].append(f"`{rel}:{line_no}` - {sample[:180]}")
    return files, ext_counts, marker_examples, marker_counts


def detect_findings(name: str, repo: Path, files: list[Path], marker_counts: Counter[str], marker_examples: dict[str, list[str]], classification: str) -> list[Finding]:
    findings: list[Finding] = []
    rels = {str(p.relative_to(repo)) for p in files}
    has_readme = any(Path(r).name.lower().startswith("readme") for r in rels)
    has_tests = any("test" in r.lower() for r in rels)
    has_paper = any(("paper" in r.lower() or r.endswith((".tex", ".pdf"))) for r in rels)
    has_results = any(("result" in r.lower() or "run" in r.lower() or "metrics" in r.lower()) for r in rels)
    has_config = any(Path(r).name in {"pyproject.toml", "package.json", "requirements.txt", "uv.lock", "requirements-lock.txt"} for r in rels)
    verdict = PRIOR_VERDICTS.get(name, "No prior verdict found in the 2026-09-12 portfolio audit.")

    if classification in {"broken", "placeholder/stub/mock", "scaffold"}:
        findings.append(Finding(
            "P0",
            name,
            f"Repository is classified as {classification}, not a complete research artifact.",
            verdict,
            "Any paper, benchmark, or project-count claim based on this component would overstate the evidence.",
            "Either demote the public claim to the observed evidence tier, or implement the missing method/data/evaluation path and retain reproducible results.",
        ))
    suppress_generic = classification in GENERIC_FINDING_SUPPRESS_CLASSES
    no_source_code = not any(p.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".cpp", ".c"} for p in files)
    if classification == "placeholder/stub/mock" and no_source_code:
        suppress_generic = True
    if suppress_generic:
        return findings
    if not has_readme:
        findings.append(Finding("P1", name, "Missing README/status entry.", "No README-like file detected at scan depth.", "External reviewers cannot reconstruct the hypothesis, method, or run boundary.", "Add README plus RESEARCH_TRUTH/EVIDENCE ledger with exact claims and non-claims."))
    if not has_tests and any(p.suffix in {".py", ".js", ".ts", ".tsx"} for p in files):
        findings.append(Finding("P1", name, "Code exists without detected tests.", "No path containing 'test' was found in the repository scan.", "Claims can regress silently and reproducibility cannot be independently checked.", "Add unit tests for metrics/data/model contracts and an end-to-end smoke test."))
    if not has_results:
        findings.append(Finding("P1", name, "No retained result artifact detected.", "No obvious result/run/metrics path was found.", "The repository cannot support empirical claims without rerunning or trusting prose.", "Commit frozen result manifests with seeds, hashes, configs, logs, and tables."))
    if has_paper and not has_results:
        findings.append(Finding("P0", name, "Paper-like material exists without obvious retained results.", "Paper/tex/pdf path detected but result artifacts were not.", "Paper claims may be unverifiable against code and data.", "Wire paper tables/figures to generated artifacts and add a reproduction script."))
    if not has_config and any(p.suffix in {".py", ".js", ".ts", ".tsx"} for p in files):
        findings.append(Finding("P1", name, "Missing dependency/environment manifest.", "Code files found, but no common Python/JS dependency manifest detected.", "Fresh reproduction is fragile or impossible.", "Add lockable dependencies and a clean setup command."))
    if marker_counts["placeholder"] or marker_counts["stub"]:
        examples = "; ".join((marker_examples["placeholder"] + marker_examples["stub"])[:5])
        findings.append(Finding("P1", name, "Unresolved placeholder/stub markers require manual triage.", examples or "Marker counts were nonzero.", "Reviewers cannot tell intentional baselines from unfinished science.", "Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work."))
    if marker_counts["claim"] and not has_results:
        examples = "; ".join(marker_examples["claim"][:5])
        findings.append(Finding("P1", name, "Claim language appears without retained evidence.", examples or "Claim markers were detected.", "Novelty or SOTA framing may be unsupported.", "Bind each claim to a checked result, citation, proof, or explicit limitation."))
    return findings


def table(rows: list[list[str]]) -> str:
    if not rows:
        return "_None detected by this scan._\n"
    header = rows[0]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in rows[1:]:
        out.append("| " + " | ".join(cell.replace("\n", " ") for cell in row) + " |")
    return "\n".join(out) + "\n"


def write_repo_report(repo: Path, prior_audit_exists: bool) -> tuple[str, str, int]:
    name = repo.name
    files, ext_counts, marker_examples, marker_counts = scan_repo(repo)
    classification = classify_repo(name, (repo / ".git").exists(), files, marker_counts)
    findings = detect_findings(name, repo, files, marker_counts, marker_examples, classification)
    verdict = PRIOR_VERDICTS.get(name, "No prior portfolio verdict available; classification is based on the fresh file scan only.")
    top_ext = ", ".join(f"{k}:{v}" for k, v in ext_counts.most_common(8)) or "no files"
    git_status = "git repo" if (repo / ".git").exists() else "repo-like directory/no local .git"
    readme = next((p for p in files if p.name.lower().startswith("readme")), None)
    readme_excerpt = read_excerpt(readme, 1200).replace("\n", " ") if readme else ""
    if len(readme_excerpt) > 900:
        readme_excerpt = readme_excerpt[:900] + "..."

    rows = [["Classification", "Evidence"]]
    rows.append([classification, verdict])
    rows.append(["complete/real", "Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification."])
    rows.append(["partial", "Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete."])
    rows.append(["pseudocode", "Flag if marker examples below contain algorithm prose without executable implementation."])
    rows.append(["scaffold", "Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research."])
    rows.append(["placeholder/stub/mock", f"placeholder={marker_counts['placeholder']}, stub={marker_counts['stub']}"])
    rows.append(["hardcoded shortcut", f"hardcoded/toy markers={marker_counts['hardcoded']}"])
    rows.append(["unused/dead", "Flag if prior audit classifies as duplicate, legacy, archive, or output-only."])
    rows.append(["untested", "Flag if code exists without detected test paths."])
    rows.append(["broken", "Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch."])
    rows.append(["missing", "Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage."])

    finding_rows = [["Severity", "File/component", "Problem", "Evidence", "Scientific impact", "Exact fix"]]
    for finding in findings:
        finding_rows.append([finding.severity, finding.component, finding.problem, finding.evidence, finding.impact, finding.fix])

    marker_block = []
    for marker, examples in marker_examples.items():
        marker_block.append(f"### {marker}\n")
        marker_block.append("\n".join(f"- {ex}" for ex in examples) if examples else "_No examples found in scanned text files._")
        marker_block.append("\n")

    checklist = []
    for sev in ["P0", "P1", "P2", "P3"]:
        checklist.append(f"## {sev} Checklist\n")
        selected = [f for f in findings if f.severity == sev]
        if sev == "P2":
            selected.append(Finding("P2", name, "Strengthen scientific comparison set.", "Baseline/citation completeness was not proven by file scan.", "Weak baselines can make a rediscovery look novel.", "Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work."))
            selected.append(Finding("P2", name, "Harden data provenance and leakage controls.", "Raw-data-to-result lineage was not fully verified by this automated pass.", "Leakage or undocumented preprocessing can invalidate conclusions.", "Add dataset cards, split manifests, licenses, hashes, and leakage tests."))
        if sev == "P3":
            selected.append(Finding("P3", name, "Improve reviewer ergonomics.", "Per-repo evidence is scattered across docs/code/results.", "Reviewers lose trust when the claim path is hard to trace.", "Add one command, one manifest, and generated paper-table provenance."))
        if not selected:
            checklist.append("_No items assigned at this severity by this pass._\n")
        for item in selected:
            checklist.append(
                f"- **WHAT:** {item.problem}\n"
                f"  **WHY:** {item.impact}\n"
                f"  **HOW:** {item.fix}\n"
                f"  **WHERE:** `{repo}` and cited files/components above.\n"
                f"  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.\n"
            )

    focused_notes = FOCUSED_NOTES.get(name, [])
    focused_block = ""
    if focused_notes:
        focused_block = "## Focused Audit Notes\n\n" + "\n".join(f"- {note}" for note in focused_notes) + "\n\n"

    body = f"""# Research Audit Checklist — {name}

Source path: `{repo}`

Audit date: {AUDIT_DATE}

Repository type: **{git_status}**

Executive verdict: **{classification}**. {verdict}

Prior portfolio audit used: **{"yes" if prior_audit_exists else "no"}**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **{len(files)}**
- Top extensions: {top_ext}
- Marker counts: todo={marker_counts['todo']}, placeholder={marker_counts['placeholder']}, stub={marker_counts['stub']}, hardcoded={marker_counts['hardcoded']}, claim-language={marker_counts['claim']}
- README excerpt: {readme_excerpt or "_No README excerpt available._"}

## Component Classification

{table(rows)}

## Critical Findings

{table(finding_rows)}

## Marker Evidence

{"".join(marker_block)}

## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.

{focused_block}
{"".join(checklist)}
"""
    out_path = OUT / f"{safe_slug(name)}.md"
    out_path.write_text(body, encoding="utf-8")
    return name, classification, len(findings)


def main() -> None:
    global AUDIT_DATE, OUT, PRIOR, ROOT

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Directory whose immediate child repositories are audited")
    parser.add_argument("--output", type=Path, help="Output directory; defaults below the NeuroCAD audits directory")
    parser.add_argument("--date", default=AUDIT_DATE, help="Audit date written into reports (YYYY-MM-DD)")
    parser.add_argument("--prior", type=Path, help="Optional prior portfolio audit used for evidence context")
    args = parser.parse_args()
    ROOT = args.root.expanduser().resolve()
    AUDIT_DATE = args.date
    OUT = (args.output or (NEUROCAD_ROOT / "audits" / f"all-repos-{AUDIT_DATE}")).expanduser().resolve()
    PRIOR = (args.prior or (ROOT / "RESEARCH_REPOSITORY_AUDIT_2026-09-12.md")).expanduser().resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    prior_audit_exists = PRIOR.exists()
    repos = [p for p in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()) if p.is_dir() and not p.name.startswith(".")]
    summary_rows = [["Repository", "Classification", "Finding count", "Report"]]
    for repo in repos:
        name, classification, finding_count = write_repo_report(repo, prior_audit_exists)
        report = f"{OUT.name}/{safe_slug(name)}.md"
        summary_rows.append([name, classification, str(finding_count), report])
    summary = f"# All-Repositories Research Audit Index — {AUDIT_DATE}\n\n"
    summary += f"Scope root: `{ROOT}`\n\n"
    summary += "This index includes every top-level directory under the scope root except hidden tool/cache directories. Each linked markdown file is a per-repo checklist artifact.\n\n"
    summary += "Active remediation queue: [WORK_QUEUE.md](WORK_QUEUE.md)\n\n"
    summary += table(summary_rows)
    summary += "\nThe generated checklists combine the 2026-09-12 human portfolio audit with a fresh source/document scan. They are intentionally skeptical: a repository remains partial unless code, data, tests, retained outputs, and paper claims can be traced end to end.\n"
    (OUT / "INDEX.md").write_text(summary, encoding="utf-8")
    print(OUT / "INDEX.md")
    print(f"reports={len(summary_rows) - 1}")


if __name__ == "__main__":
    main()
