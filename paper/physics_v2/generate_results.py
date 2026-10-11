"""Generate the paper's LaTeX results strictly from locked confirmatory artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tex(value: str) -> str:
    substitutions = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(substitutions.get(character, character) for character in value)


def _endpoint(metrics: dict[str, Any], name: str) -> tuple[int, int, float, float]:
    endpoint = metrics["endpoints"][name]
    lower, upper = endpoint["wilson_95"]
    return int(endpoint["successes"]), int(endpoint["total"]), float(lower), float(upper)


def generate(run_dir: Path, ledger_path: Path, output: Path) -> None:
    metrics_path = run_dir / "metrics.json"
    manifest_path = run_dir / "manifest.json"
    metrics = _load(metrics_path)
    manifest = _load(manifest_path)
    ledger = _load(ledger_path)
    if manifest.get("phase") != "confirmatory" or manifest.get("case_count") != 216:
        raise ValueError("paper generation requires the 216-case confirmatory manifest")
    if ledger.get("status") != "EXECUTED_ONCE" or ledger.get("metrics_sha256") != _sha256(metrics_path):
        raise ValueError("execution ledger does not authenticate the confirmatory metrics")
    if metrics.get("disposition") not in {"SUPPORTED_WITHIN_CONTROLLED_CONTRACT", "MIXED", "INVALID"}:
        raise ValueError("unknown confirmatory disposition")

    rows = []
    labels = (
        ("Valid full acceptance", "valid_full_acceptance"),
        ("Valid full determinism", "valid_full_determinism"),
        ("Full geometry contradiction detection", "full_geometry_input_detection"),
        ("Full material contradiction detection", "full_material_input_detection"),
        ("Full load contradiction detection", "full_load_input_detection"),
        ("Full stale-hash detection", "full_stale_expected_hash_detection"),
        ("Hash-only semantic non-detection", "hash_only_semantic_non_detection"),
        ("Unbound semantic non-detection", "unbound_semantic_non_detection"),
        ("Full post-mutation detection", "full_post_mutation_detection"),
        ("Hash-only post-mutation detection", "hash_only_post_mutation_detection"),
        ("Unbound post-mutation non-detection", "unbound_post_mutation_non_detection"),
        ("Full non-geometric specificity", "full_non_geometric_specificity"),
        ("Hash-only non-geometric specificity", "hash_only_non_geometric_specificity"),
    )
    for label, key in labels:
        successes, total, lower, upper = _endpoint(metrics, key)
        rows.append(f"{_tex(label)} & {successes}/{total} & {lower:.3f}--{upper:.3f} \\\\")

    paired = metrics["paired_full_vs_unbound_post_mutation"]
    timing = metrics["timing_diagnostics"]
    sizes = metrics["report_size_bytes"]
    disposition = _tex(str(metrics["disposition"]))
    commit = _tex(str(manifest["git_commit"]))
    all_successes = sum(_endpoint(metrics, key)[0] for _, key in labels)
    all_total = sum(_endpoint(metrics, key)[1] for _, key in labels)
    abstract = (
        f"The locked 216-case run was classified \\texttt{{{disposition}}}; "
        f"the predeclared arm-specific endpoints recorded {all_successes}/{all_total} expected outcomes. "
        f"For post-result mutation, the full-versus-unbound discordance was "
        f"{paired['full_only']} to {paired['unbound_only']} "
        f"(exact two-sided McNemar $p={paired['exact_two_sided_mcnemar_p']:.3g}$)."
    )
    body = rf"""
The single protected execution completed {metrics["case_count"]} cases and was
classified \texttt{{{disposition}}}. Table~\ref{{tab:endpoints}} reports every
predeclared arm-specific endpoint. The intervals are descriptive Wilson 95\%
intervals for the fixed matrix.

\begin{{table*}}[t]
\centering
\caption{{Confirmatory contract endpoints. ``Expected outcome'' includes both
detection where a mechanism applies and declared non-detection where an arm has
no such mechanism.}}
\label{{tab:endpoints}}
\begin{{tabular}}{{@{{}}lcc@{{}}}}
\toprule
Endpoint & Expected outcomes & Wilson 95\% interval \\
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabular}}
\end{{table*}}

For the paired post-result geometry mutations, the full arm alone detected
{paired["full_only"]} cases and the unbound arm alone detected
{paired["unbound_only"]} cases; the exact two-sided McNemar value was
$p={paired["exact_two_sided_mcnemar_p"]:.6g}$. This comparison describes the
presence or absence of the preregistered dependency mechanism and is not a
population-effect estimate.

On this host, median recorded successful evaluation times were
{timing["full"]["median_ms"]:.3f} ms for full binding
($n={timing["full"]["count"]}$), {timing["hash_only"]["median_ms"]:.3f} ms for
hash-only ($n={timing["hash_only"]["count"]}$), and
{timing["unbound"]["median_ms"]:.3f} ms for unbound requests
($n={timing["unbound"]["count"]}$). Failed evaluations have no elapsed-time
record, so these samples are conditional and must not be compared as balanced
performance arms. Corresponding p95 times were {timing["full"]["p95_ms"]:.3f},
{timing["hash_only"]["p95_ms"]:.3f}, and {timing["unbound"]["p95_ms"]:.3f} ms.
The median serialized full receipt was {sizes["median"]} bytes and the maximum
was {sizes["maximum"]} bytes. These are local diagnostics only.
""".strip()
    text = (
        "\\resultavailabletrue\n"
        f"\\newcommand{{\\ResultCommit}}{{{commit}}}\n"
        f"\\newcommand{{\\ResultAbstract}}{{{abstract}}}\n"
        "\\newcommand{\\ResultSection}{%\n"
        f"{body}\n"
        "}\n"
    )
    output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite an existing generated result file")
    generate(args.run_dir, args.ledger, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
