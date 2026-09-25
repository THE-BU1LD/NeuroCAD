# Conference readiness checklist

The exhaustive implementation/action inventory is
`audit/ULTIMATE_IMPLEMENTATION_CHECKLIST.md`; this file is the compact venue gate.

Each row states severity, current evidence, required change, and verification.

## A. Project understanding
- [x] **P0 — implemented.** Map canonical and archival paths. Evidence: `audit/REPOSITORY_MAP.md`. Verify: every manuscript claim has an evidence path.
## B. Research question
- [x] **P1 — implemented.** Narrow to controlled compiler correctness. Evidence: `QUESTION.md`, `research/HYPOTHESES.md`. Verify: no learned/general-CAD claim.
## C. Mathematical formulation
- [x] **P1 — implemented.** Formalize partial compiler, IR, validation, and mesh checks. Evidence: `research/MATHEMATICAL_SPEC.md`. Verify against code/tests.
## D. Core model implementation
- [x] **P0 — engineering-verified.** Real deterministic compiler; no trained model claimed. Evidence: `core/`, maintained tests. Verify: imports/forward compilation pass.
## E. Data
- [ ] **P1 — protocol frozen, external data still absent.** Synthetic generator is deterministic but circular for external validity. `research/protocols/EXTERNAL_EVALUATION_V0.md` freezes independent authorship, adjudication, provenance, hashing, exclusions, source/data freeze, and outcome-access rules. Required: materialize the independent, licensed, hashed prompt/spec set. Verify: challenge receipt and leakage audit before outcome access.
## F. Baselines
- [ ] **P1 — improved but incomplete.** Fixed, raw, normalized-dimensions, and retrieval controls exist. The unit-aware control isolates normalization but remains weak. The external protocol requires a strong grammar-independent comparator before any comparative language-understanding claim. Required: freeze and execute that comparator reproducibly, or weaken comparative claims. Verify: same challenge, scoring, retry budget, retained outputs, and pre-outcome identity receipt.
## G. Training
- [x] **P3 — not applicable.** No learned parameters, optimizer, checkpoint, or tuning. Verify: no manuscript training claim.
## H. Evaluation
- [x] **P0 — controlled evaluation implemented.** Exact signatures, static validation, and kernel checks are separate. Evidence: `core/research_suite.py`. The external protocol separately defines valid semantic exactness and fail-closed rejection as primary endpoints. Verify: fail-closed tests and raw records.
## I. Ablations
- [ ] **P1 — partial.** Constraint removal and bundled frontend removal exist; componentwise parser/unit/feature ablations do not. Required: isolate claimed components or weaken claims. Verify flags alter executed computation.
## J. Statistics
- [x] **P1 — adequate for deterministic paired tasks.** Wilson summaries and exact McNemar recorded; malformed repeats are not treated as independent. External paired comparisons are preregistered as exact two-sided McNemar plus prompt-clustered bootstrap. Verify: raw prompt is the unit.
## K. Robustness
- [ ] **P2 — protocol defined, evidence absent.** Bounds/fuzz/failure tests and a 24-case immutable audit-authored challenge pass, but independent authorship is absent. The external protocol defines a frozen perturbation extension for semantics-preserving and semantics-breaking transformations. Required: independently materialize and hash that matrix before outcome access. Verify separate from IID evidence.
## L. OOD/generalization
- [ ] **P1 — protocol defined, outcomes absent.** Template-held-out labels are not real OOD. The external protocol requires independently authored prompts, wording/unit shifts, explicit provenance, and blinded source/data freeze. Required: execute the frozen external challenge. Verify no parser edits after label access.
## M. Scaling
- [x] **P2 — engineering-verified.** Node/depth caps and depth 129 rejection exist. Evidence: NC-EXP-007/tests. Verify no recursion/resource failure at boundary.
## N. Efficiency
- [ ] **P2 — partial.** Runtime/memory diagnostics exist, no portable kernel throughput study. Required: declared hardware and repeated timing protocol. Verify raw timings and warmup policy.
## O. Reproducibility
- [x] **P0 — locally verified.** `NC-REPRO-508EC40` was produced from clean commit `508ec404dd520ae16f2b4d3cf211d5b1fa46b800` with pinned CPython/lock, source hashes, 1,212 artifact hashes, 240 fresh kernel compilations, and no reuse. External evaluation additionally requires exact Git/source/data/scorer/comparator/OpenSCAD identities before label opening. Independent cross-machine reproduction remains an external gate.
## P. Tests
- [x] **P0 — engineering-verified.** Broad parser/IR/kernel/CLI/failure/provenance suite. Claim-boundary and external-protocol regressions additionally fail CI if the falsified historical claim, no-trained-model boundary, unsupported-domain quarantine, or pre-outcome external-evaluation gates drift. Verify full suite with loopback permission plus static gates.
## Q. Code quality
- [x] **P1 — verified.** Ruff and mypy pass. Verify after every edit.
## R. Documentation
- [x] **P1 — repaired.** Capability boundaries and provenance caveats explicit. Verify stale no-Git statements absent.
## S. Related work
- [x] **P1 — verified.** All 15 manuscript references and their comparative characterizations were checked against primary CVF/arXiv records. Evidence: `literature/CITATION_AUDIT_20260913.md`.
## T. Novelty
- [x] **P0 — negative finding.** No algorithmic novelty. Required action: position as systems case study. Verify no novelty/SOTA language.
## U. Paper
- [x] **P1 — locally evidence-bound.** The manuscript's primary controlled table is bound to `NC-REPRO-508EC40`; claims remain deliberately narrow because the data and authoring are not independent. The external protocol may enter the methods/evaluation plan now, but external results enter the manuscript only after the frozen challenge is actually executed. Required for submission: venue formatting and the external evidence in W.
## V. Release package
- [ ] **P1 — local only.** Build tooling exists; public tag/CI/install receipts absent. `EXTERNAL_EXECUTION_REQUIRED`. Verify anonymous exact-tag install.
## W. External execution requirements
- [ ] **P1 — blocked externally.** Independent challenge authors/adjudicator, licensed external prompt/spec data, strong grammar-independent comparator execution, public CI/release, external replication, physical fabrication, and authorized VeriCodeGen outcomes remain outside current evidence. `research/protocols/EXTERNAL_EVALUATION_V0.md` defines the external challenge gate but does not satisfy it by itself. Verify with immutable receipts; never infer success.

## Current decision

**MAJOR SCIENTIFIC REVISION.** Core engineering and exact-revision local
reproduction are credible, and the external-evaluation protocol is now frozen.
Conference-level scientific evidence remains incomplete because the headline benchmark
is synthetic and project-authored, the compatible baselines are weak, and no independent
challenge outcome, strong external comparator result, or independent replication exists.
