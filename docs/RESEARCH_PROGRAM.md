# Research program

## Claims

- **Current claim:** the retained controlled suite reports exact compilation and kernel-validity outcomes for a narrow synthetic grammar, but its historical full run is not bound to producing source.
- **Best defensible claim:** NeuroCAD is a well-tested, fail-closed reference compiler and evidence harness for an explicit dimensioned-English-to-CSG contract; current evidence is engineering/development evidence.
- **Long-term ambitious claim:** explicit typed intent and executable verification improve reliability and editability of broad text-to-parametric-CAD generation. This remains untested here and is now adjacent to systems such as CIT-CAD, CAD-Llama, and Pointer-CAD.

Failure is scientifically meaningful: any silent acceptance, semantic mismatch, invalid kernel artifact, inability to beat the strongest compatible baseline on independent prompts, or lower paired-effect confidence bound at or below the frozen margin falsifies the corresponding hypothesis.

## Baselines

| Tier | Baseline | State | Rationale |
|---|---|---|---|
| Trivial | Fixed 80 mm box | Implemented | Detects degenerate constant success |
| Surface | Raw number extraction, no units/features | Implemented | Tests whether copying numerals explains performance |
| Standard simple | Unit-normalized dimensions only | Implemented | Isolates unit-aware dimension extraction from features |
| Memorization | Train-only nearest-neighbor retrieval | Implemented | Detects template/example copying |
| Strongest feasible current | Reviewed grammar-independent structured parser or constrained LLM/CadQuery compiler | Missing | Must share prompts, supported subset, frozen outputs, and kernel checks |
| Contemporary external | CAD-Llama/CAD-Coder/CIT-CAD-class system | Blocked | Task/representation/API/compute mapping is not yet frozen; direct published-score comparison would be invalid |

## Experiment specifications

| ID | Hypothesis / independent variable | Dependent variables | Controls and data | Seeds/statistics | Success / failure | Artifact | Compute |
|---|---|---|---|---|---|---|---|
| NC-EXP-001 | Full compiler vs five declared systems | semantic exactness, valid output, intervention consistency | frozen controlled JSONL; identical expected signatures | deterministic seed; paired exact McNemar; effect sizes | 100% and advantage over strongest simple control / any mismatch or no advantage | per-task JSON + aggregate | CPU minutes |
| NC-EXP-002 | Typed IR preserves invariants | validation, round trip, deterministic export | generated six-primitive/Boolean/reference programs | one frozen generator seed; no population inference | all pass / any failure | JSONL + failures | CPU minutes |
| NC-EXP-003 | Invalid classes fail closed | rejection and classified error | unique generated fixtures across eight classes | deterministic regression only; no binomial CI | all reject / any acceptance or crash | invalid JSONL | CPU minutes |
| NC-EXP-004 | Declared constraints vs removed constraints | paired corruption detection | identical program/corruption; only constraint presence differs | paired effect; exact test when needed | at least +90 pp / below margin | paired records | CPU seconds |
| NC-EXP-005 | Named parameter edit | validate/round-trip/export success | identical edit procedure on generated programs | deterministic; all-case acceptance | all pass / any failure | edit records | CPU seconds |
| NC-EXP-006 | OpenSCAD execution | compile, finite vertices, volume, watertightness, winding, components, extents | preselected family-balanced tasks, fresh artifacts | all selected cases; Wilson interval descriptive only | all pass / missing kernel or any failure | IR/SCAD/STL/PNG/validation | CPU hours; storage ~tens of MB |
| NC-EXP-007 | Hierarchy depth | validity and export through declared bound | constructed depths 1–129 | deterministic boundary test | 128 accepted, 129 explicit reject / otherwise | complexity records/plot | CPU seconds |
| NC-EXP-008 | Independent prompt generalization | semantic exactness, rejection precision, kernel validity | blind outside-authored in-scope and out-of-scope prompts; deduplicated before freeze | sample-size simulation before freeze; paired bootstrap CI + McNemar; Holm secondary corrections | lower 95% paired-effect bound >10 pp, no silent false accept / otherwise | frozen data, predictions, failures | CPU hours plus annotation |
| NC-EXP-009 | Human editability | task success, time, error, workload | counterbalanced users/tasks; typed IR vs chosen CAD/code baseline | preregistered mixed-effects or paired analysis after pilot | frozen practical margin / missed margin | anonymized protocol/results | BLOCKED by recruitment/ethics |
| NC-EXP-010 | Physical enclosure validity | fit, dimensional error, print failure | predeclared printer/material/profile, calibration coupons, repeated parts | repeat prints across days/printers where feasible | frozen tolerances / any safety or fit violation | measurement sheets/photos/hashes | BLOCKED by hardware |

## Ablation matrix

| Variant | Full parser | Unit normalization | Feature semantics | Declared constraints | Metric |
|---|---:|---:|---:|---:|---|
| Full | yes | yes | yes | yes | semantic exactness + drift detection |
| Normalized dimensions only | no | yes | no | no | semantic exactness |
| Raw numbers | no | no | no | no | semantic exactness |
| No constraints | yes | yes | yes | no | corruption detection |
| Units only removed | yes | no | yes | yes | **missing; implement before causal unit claim** |
| Feature parser only removed | yes | yes | no | yes | **missing; implement before causal feature claim** |
| Lexical aliases removed | restricted | yes | yes | yes | **missing; optional diagnostic** |

The executable declarations are in `configs/ablation_manifest.json`. The current raw-number comparator is a coupled ablation and cannot attribute its entire gap to unit normalization.

## Sensitivity and robustness

- Generator-seed sensitivity: use multiple predeclared seeds only for robustness; do not treat deterministic template variants as independent population samples.
- Data-size sensitivity: report unique prompts and template/category effective sample sizes.
- Numeric boundaries: minimum/maximum dimensions, feature count, graph nodes/depth, non-finite and near-zero values.
- Linguistic perturbations: whitespace, Unicode multiplication sign, unit aliases, named dimensions, order changes, and explicitly unsupported clauses.
- Distribution shift: blind human-authored prompts are mandatory before any natural-language generalization claim.
- Kernel shift: record OpenSCAD executable digest/version; compare semantic outcomes separately from mesh-byte identity.

## Failure analysis

Persist every per-example expected signature, actual signature, error category, runtime status, and artifact path. Review all system failures, high-confidence false accepts, cross-family clusters, unit errors, feature-count errors, and kernel discrepancies. Select qualitative examples before opening outcomes. Do not use a success-only gallery.

## Statistical policy

Engineering invariant suites use all-case acceptance and descriptive intervals only where the cases are meaningfully distinct. Independent prompt evaluation should report paired absolute effects with bootstrap confidence intervals and exact McNemar tests; adjust only genuinely multiple secondary comparisons. Human studies require a pilot-driven power analysis and participant/task-aware model. Timing is diagnostic unless repetitions, warm-up, and machine isolation are preregistered.
