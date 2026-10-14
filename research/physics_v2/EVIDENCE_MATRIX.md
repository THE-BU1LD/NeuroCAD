# Claim-to-evidence matrix

Every result-bearing paper statement must terminate in retained evidence. The
scientific unit is a frozen case, not a repeated execution, table row, or
receipt field.

| Claim | Experiment | Raw artifact | Analysis | Paper location | Status |
|---|---|---|---|---|---|
| P2-C1: valid bound requests retain dependency identities and deterministic scientific fields | 48 valid cases; full arm evaluated twice | `runs/NC-PHYS-V2-CONFIRM-001/raw_results.jsonl` | `metrics.json` endpoints `valid_full_acceptance` and `valid_full_determinism`; post-outcome `audit.json` | Abstract; Results; Table 3 | `48/48`, `48/48`; supported in frozen matrix |
| P2-C2: full binding rejects four declared contradiction classes | 24 geometry, 24 material, 24 load, and 24 stale-hash cases | same raw JSONL, all 96 records retained | four full-detection endpoints; family counts recomputed by `audit_results.py` | Results; Table 3 | `96/96`; supported in frozen matrix |
| P2-C2 control boundary: semantic checks absent from hash-only and unbound arms do not receive detection credit | 72 semantic contradiction cases per control arm | same raw JSONL | `hash_only_semantic_non_detection` and `unbound_semantic_non_detection` | Table 3 caption and rows | `72/72` expected non-detections in each arm |
| P2-C3: bound receipts detect declared post-result geometry drift | 48 paired mutations across full, hash-only, and unbound arms | same raw JSONL | three post-mutation endpoints; exact McNemar calculation in `metrics.json` | Abstract; Results; Table 3 | full `48/48`, hash-only `48/48`, unbound `0/48`; supported only as mechanism contrast |
| P2-C4: label/revision-only changes do not invalidate canonical geometry | 24 non-geometric mutation cases | same raw JSONL | full and hash-only specificity endpoints | Results; Table 3 | `24/24` in each bound arm |
| P2-C5: bounded local diagnostic overhead | successful evaluations within the single host run | per-arm elapsed times and serialized receipt sizes in raw JSONL | descriptive medians/p95 and sample counts in `metrics.json` | Results, final paragraph | descriptive one-host evidence only; failed evaluations have no timing sample |
| P2-C6: new provenance/digital-thread algorithm | literature audit | `LITERATURE_REVIEW.md` | prior-art comparison and novelty adjudication | Related Work | `REJECTED` |
| P2-C7: physical accuracy, solver validity, safety, or certification | no admissible experiment | none | prohibited by protocol and claim ledger | Abstract; Threats; Discussion; Conclusion | `NOT_SUPPORTED / PROHIBITED` |
| P2-C8: enterprise CAD/CAE or PLM generalization | no admissible experiment | none | prohibited by protocol and claim ledger | Threats; Discussion; Conclusion | `NOT_SUPPORTED / PROHIBITED` |

## Integrity chain

The immutable identity chain is:

`freeze.json` -> frozen case JSONL -> single-attempt execution ledger -> raw
JSONL -> metrics and manifest -> post-outcome audit -> generated LaTeX table ->
compiled PDF.

The hashes for every arrow are retained in the execution ledger, run manifest,
results report, canonical research state, clean-checkout verification receipt,
and release manifest. The post-outcome audit reads artifacts only and performs
no case execution.

## Statistical and wording audit

- Wilson intervals describe the fixed matrix; they are not population
  confidence claims.
- The exact two-sided McNemar value summarizes the 48-to-0 paired discordance;
  the preregistered decision rule is still 100% conformance.
- The unbound result means that this arm exposes no machine-verifiable geometry
  freshness mechanism. It is not evidence that every unbound workflow fails.
- Runtime and size measurements are conditional one-host diagnostics, not
  balanced performance benchmarks.

