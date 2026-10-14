# Physics v2 checkpoint audit

**Audit date:** 2026-10-11  
**Scientific disposition:** `SUPPORTED_WITHIN_CONTROLLED_CONTRACT`  
**Audit boundary:** internal release audit; not independent reproduction,
physical validation, safety certification, or external adjudication.

This document maps the ten project-pipeline checkpoints to retained evidence.
It does not reopen the frozen protocol or authorize another version-1
confirmatory execution.

| Checkpoint | Status | Retained evidence | Residual boundary |
|---|---|---|---|
| 1. Idea ready | `PASS_BOUNDED` | `LITERATURE_REVIEW.md`, `ADVERSARIAL_REVIEW.md`, `CLAIM_LEDGER.md`, canonical state | Algorithmic novelty was rejected; the contribution is a bounded executable contract. |
| 2. Model specification ready | `PASS` | `MODEL_SPEC.md`, pre-results paper history | No physical, solver, safety, or enterprise-system model is specified. |
| 3. Methodology ready | `PASS` | `PROTOCOL.md`, frozen matrix design, endpoints and 100% decision rules | Synthetic fixed-matrix conformance only; OOD and scaling claims are out of scope. |
| 4. Model implemented | `PASS_ENGINEERING` | `core/physics_context.py`, `core/physics.py`, CLI integration, unit and integration tests | Engineering fidelity does not establish scientific independence or physical validity. |
| 5. Experiment system implemented | `PASS_ENGINEERING` | `study.py`, `audit_results.py`, generator, manifests, resource gates, ledgers | The internal harness and cases share authorship with the implementation. |
| 6. Run ready | `EXECUTED_ONCE` | retained `DEV-001` failure, `DEV-002` result, fixed two-revision budget | Development history is not confirmatory evidence. |
| 7. Confirmatory protocol frozen | `PASS` | `frozen/freeze.json`, 216-case JSONL, source and semantic hashes | Any version-1 scientific source or endpoint change requires a successor protocol. |
| 8. Evidence locked | `PASS` | execution ledger, raw JSONL, metrics, manifest, post-outcome audit, evidence matrix | No failed case was removed and no protected rerun is permitted. |
| 9. Verified | `PASS_INTERNAL_CLEAN_CHECKOUT`; `EXTERNAL_NOT_YET` | clean-checkout receipt, regenerated analysis, paper compile/text comparison, test and static-analysis receipts | Independent execution, custody, and adjudication remain open. |
| 10. Research complete | `TERMINAL_WITHIN_CONTROLLED_CONTRACT`; `RELEASE_PACKAGED` | final paper, arXiv source, release manifest, hashes, external handoff | Author metadata, arXiv license/category choices, submission, and external reproduction require external action. |

## Pipeline decisions

- Plots, heatmaps, OOD tests, scaling tests, training curves, and
  parameter-matched controls are not silently omitted evidence. They are not
  applicable to the deterministic receipt contract or are outside the frozen
  claim. The paper uses exact tables because the evidence is a fixed binary
  conformance matrix.
- The hash-only arm is the mechanism ablation. The unbound arm is the
  mechanism-off control. No compute-matched performance claim is made because
  the scientific question is contract behavior rather than predictive
  performance.
- The successful outcome does not authorize additional confirmatory work.
  Stronger physical, enterprise, or independently authored evidence belongs in
  a separately versioned successor study.

## Open external actions

1. Confirm the exact public author name and affiliation.
2. Choose the arXiv license and final subject category.
3. Submit through arXiv and inspect the platform-generated PDF.
4. Obtain execution, custody, and adjudication from an independent party using
   `EXTERNAL_REPRODUCTION.md`.

