# Claim-to-evidence matrix

| Claim | Implementation | Dataset | Experiment | Artifact | Status |
|---|---|---|---|---|---|
| Bounded prompts compile to exact declared semantics | parser → IR → signature evaluator | synthetic compiler stress | NC-EXP-001 | historical FULL per-task results | PRELIMINARY |
| Compiler outperforms fixed/raw/retrieval controls on controlled set | five-system benchmark | synthetic compiler stress | NC-EXP-001 | historical FULL results | PRELIMINARY |
| Current source reproduces historical 240/240 result | hardened runner exists | historical FULL | fresh full rerun required | no source-bound current full manifest | UNTESTED |
| Canonical IR validates, round-trips, and exports deterministically | IR/schema/parser/exporter | generated IR programs | NC-EXP-002 | historical JSONL/results + current tests | SUPPORTED as engineering invariant |
| Invalid inputs fail closed | parser/IR validators | eight-category fixtures + prompt challenge | NC-EXP-003/challenge | raw invalid records | SUPPORTED for enumerated categories |
| Constraints detect injected dimensional drift | declared constraint validator | paired generated corruptions | NC-EXP-004 | historical paired aggregate/current tests | SUPPORTED narrowly |
| Unit normalization alone causes the frontend gain | partial comparators | controlled prompts | coupled frontend ablation | no isolated unit-only variant | UNSUPPORTED |
| Programs are machine-editable | named parameter edit path | generated boxes | NC-EXP-005 | historical edit records/current tests | SUPPORTED narrowly |
| Users can edit designs effectively | no executed human study | none | NC-EXP-009 | protocol only | UNTESTED |
| Selected programs execute as valid OpenSCAD solids | compiler and mesh verifier | selected stress tasks | NC-EXP-006 | 240 historical STL/validation records | PRELIMINARY because provenance/reuse limits |
| Current source passes fresh kernel smoke | executable runner | small diagnostic set | smoke run | current audit artifact/receipt when retained | SUPPORTED as development evidence |
| Mesh validity proves manufacturability or fit | no such verifier | none | physical protocol only | none | UNSUPPORTED |
| Enclosure workflow preserves typed revisions and verified bundle bytes | enclosure/project/integration modules | test fixtures | product integration tests | test receipts | SUPPORTED locally |
| Calibration improves physical fit | calibration estimator only | no real measurements | NC-EXP-010 | none | UNTESTED |
| NeuroCAD is general text-to-CAD or state of the art | no broad model/task | no external benchmark | none | none | UNSUPPORTED |
| NeuroCAD implements STEP/BREP | historical fake route disabled | none | none | negative archive evidence | NEGATIVE |
| Historical typed parser caused learned-model improvement | no valid model calls | historical scripted fixtures | VeriCodeGen Stage 1 | audit ledger | NEGATIVE |
| VeriCodeGen S3 has model outcomes | pre-outcome tooling only | no candidate pool | not authorized | pre-outcome status | BLOCKED |
| Release is independently reproducible | workflows and provenance tooling exist | N/A | exact-revision external run | no hosted/tag/anonymous-install receipt | BLOCKED |

Quantitative historical claims must retain “historical development evidence” and link to the immutable run artifact. Current-source claims require a new source-bound manifest. No table or figure may be manually updated from prose.
