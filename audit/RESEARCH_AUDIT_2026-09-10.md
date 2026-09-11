# NeuroCAD research audit — 2026-09-10

## Verdict

NeuroCAD's maintained path is a real, bounded deterministic CAD compiler with a strong fail-closed engineering posture. It is not a trained model and should not be evaluated or described as one. The largest remaining conference blocker is not missing parser implementation; it is **external validity**. Current headline compiler evidence is generated from the same declared grammar as the parser, and the prior adversarial challenge was audit-authored after source inspection. Those results are useful engineering evidence but do not establish independent natural-language generalization.

The historical typed-parser causal claim remains **falsified**. Nothing in this audit changes that result.

Current research state: **EVIDENCE_PARTIAL**.

## 1. Model / method audit

### Supported method

The supported method is:

`prompt -> strict deterministic parser -> DesignGraph compatibility representation -> canonical typed IR -> semantic validation -> deterministic OpenSCAD -> optional OpenSCAD/STL verification`

`MODEL_CARD.md` correctly states that the supported pipeline contains no trained parameters, optimizer, training data, training seeds, or checkpoint. Any learned-model experiment is a distinct scientific study and must not be folded into the deterministic compiler evidence.

### Risk

Language such as "model", "AI CAD", or learned geometric reasoning would overstate the current method. The repository already contains historical neural/SDF artifacts and successor VeriCodeGen/S3 research controls, so accidental claim drift is plausible even though the production compiler is deterministic.

### Change in this audit

`tests/test_research_claim_boundaries.py` now makes the no-trained-model boundary and the falsified typed-parser result CI-visible. A future edit that silently rewrites those boundaries will fail the maintained test suite.

## 2. Prompt parser audit

### What is strong

- `core/prompt_engine.py` uses anchored whole-prompt contract checks rather than treating partial number extraction as understanding.
- normalization has a losslessness check, preventing unsupported characters from being silently erased and then accepted;
- overall dimension extraction rejects multiple ambiguous dimension sequences;
- feature counts reject signed, fractional, zero, and excessive counts;
- `core/prompt_frontend.py` extends only narrow already-parsed cases and may set `prompt_fully_consumed` only after a full-string match plus explicit-field checks;
- validation requires supported domain, recognized prompt, explicit overall dimensions, and a fully consumed prompt before compilation.

### Important source-level caveat

`core/prompt_engine.py` still contains old helper implementations for aircraft, vehicle, mechanism, and furniture geometry. The public `generate_design()` path explicitly quarantines those helpers and returns an unsupported empty design for those domains, so they are not current product functionality. Their continued presence is nevertheless a maintenance hazard because they can generate plausible-looking default geometry if reconnected accidentally.

### Change in this audit

A new regression test exercises aircraft, car, motor, and desk prompts and requires all four to return no program, empty SCAD, and an explicit unsupported-domain validation error. This turns the legacy-generator quarantine from a comment-level invariant into an executable gate.

### Remaining parser research gap

The parser is well tested against its declared grammar. What remains scientifically weak is evidence that independently authored in-scope prompts are handled correctly without being shaped by the same authors/templates that shaped the parser.

## 3. IR / generation audit

### What is strong

- `text_to_cad.py` refuses to build canonical IR when prompt validation fails;
- `core/ir_parser.py` applies JSON Schema validation and then semantic program validation before accepting IR;
- serialization uses sorted keys and disallows NaN, supporting deterministic byte-level outputs;
- canonical IR and SCAD are separate from the compatibility `DesignGraph`, which reduces ambiguity about the actual compiled artifact;
- OpenSCAD/kernel checks are distinct from static semantic exactness rather than being treated as proof of the same property.

### Remaining engineering/research boundaries

OpenSCAD compile success, watertightness, positive volume, extents, and connected-component checks establish bounded mesh integrity. They do not prove physical fit, printability, tolerance, load-bearing behavior, regulatory compliance, or manufacturability. These must remain explicit non-claims.

## 4. Tests and CI audit

The current CI is unusually strong for a research repository:

- maintained pytest suite on multiple CPython versions;
- Ruff, mypy, Bandit, pip-audit, and `pip check`;
- OpenSCAD-backed CLI/research smoke execution;
- wheel and sdist builds;
- deterministic repeat-build comparison;
- clean wheel/sdist install smoke tests;
- portable Linux/macOS/Windows product tests;
- Git-history high-confidence secret scanning;
- retained JUnit artifacts even on failures.

The engineering test problem is therefore not simple coverage volume. The scientific weakness is **who authored the test population and when**.

## 5. Pseudocode, placeholders, and disconnected surfaces

The supported compiler path inspected in this audit is implemented code rather than pseudocode. The known problematic surfaces are explicitly historical/disconnected:

- legacy STEP-writing behavior that emitted marker text rather than STEP;
- broken historical kernel paths;
- older disconnected schema/NLP/evaluation modules;
- historical root-level scripts/tests that are not part of the maintained test surface.

The maintained source should continue to resist pulling those artifacts back into product or manuscript claims merely because they exist in the repository.

The major "placeholder" in the conference story is methodological rather than algorithmic: the independent challenge dataset, external adjudication, strong grammar-independent comparator, and independent replication have not yet been materialized.

## 6. Scientific assumptions audit

### H1 / semantic exactness versus baselines

The current generated benchmark is useful for controlled compiler conformance, but it is circular evidence for external validity because tasks are emitted from the declared grammar. Fixed-box, raw-number, normalized-dimensions, and nearest-neighbor controls are informative mechanism checks but too weak by themselves for a broad comparative language-understanding claim.

**Required interpretation:** keep claims bounded to the controlled compiler unless a strong grammar-independent comparator and independent prompt set are executed under a frozen protocol.

### H2 / round-trip and deterministic export

This is a legitimate engineering claim for the canonical representation. It should not be promoted into a natural-language generalization claim.

### H3 / invalid-input rejection

Fail-closed rejection is a meaningful safety/engineering property. Independent invalid prompts are still needed because generated malformed cases can share assumptions with the validator.

### H4 / constraint ablation

The existing corruption ablation demonstrates that declared constraints detect parameter drift relative to those constraints. It does **not** show automatic inference of design intent or a general constraint solver.

### H5 / kernel-backed solids

Passing OpenSCAD and mesh checks demonstrates bounded executable geometry. It does not establish manufacturing or physical correctness.

## 7. Reproducibility audit

### Strong current controls

- source snapshot hashing;
- requirements lock digest;
- package-version checks;
- Python/platform capture;
- OpenSCAD executable/version/hash capture where available;
- fresh-output-only research runs rather than silent resume/overwrite;
- raw artifact retention and deterministic result separation from timing measurements.

### Remaining gaps

1. independent challenge data does not yet exist;
2. no external authorship/adjudication receipt exists;
3. no strong grammar-independent comparator is frozen/executed for the deterministic compiler paper;
4. no independent replication receipt exists;
5. historical headline evidence remains weaker than a fresh exact-source-bound run;
6. public exact-tag/release/install evidence is still distinct from local or PR CI evidence;
7. physical fabrication evidence is absent and should remain optional/supporting, not silently inferred from STL validity.

## 8. Highest-value change completed

`research/protocols/EXTERNAL_EVALUATION_V0.md` now preregisters the missing independent evaluation layer without fabricating any outcome. It requires:

- external prompt authors who did not implement the evaluated parser rules;
- separate adjudication;
- a minimum independently authored valid + reject challenge population;
- explicit provenance/permission;
- challenge JSONL hashing;
- exact source, lock, scorer, comparator, and optional OpenSCAD identities before label opening;
- separate valid semantic-exact and fail-closed rejection primary endpoints;
- exact paired McNemar comparison and prompt-level bootstrap for paired systems;
- pre-outcome exclusions only;
- no parser edits, prompt rewriting, hidden task deletion, or result rescue after label access;
- a strong grammar-independent comparator before any broad comparative language claim;
- an explicit statement that protocol creation alone adds no positive result.

`tests/test_external_evaluation_protocol.py` makes those core integrity conditions fail closed under CI.

## 9. Next execution gates, in order

1. **Independent challenge authorship:** recruit at least two non-implementer authors plus a separate adjudicator and materialize the licensed prompt/spec set without exposing labels to parser developers.
2. **Freeze receipt:** bind exact Git/source snapshot, lock, challenge hash, scorer, retry budget, comparator identities, and OpenSCAD identity before outcomes are opened.
3. **Strong comparator:** select and freeze a grammar-independent prompt-to-CAD comparator or explicitly narrow the paper's comparative claims.
4. **Confirmatory external run:** run NeuroCAD and all frozen comparators once under the protocol; retain every task, failure, exclusion, and raw output.
5. **Fresh source-bound internal rerun:** regenerate the controlled research suite from a clean exact revision with no artifact reuse, so historical resumed/source-unbound evidence is not the primary table.
6. **Independent replication:** have a separate operator execute the documented reproduction path from the exact public revision/tag.
7. **Paper reconciliation:** update every table and abstract claim only from the new retained artifacts; leave negative/falsified historical results unchanged.

Until gates 1–4 are complete, the defensible conference posture is a systems case study with strong engineering evidence and incomplete external scientific evidence—not a general text-to-CAD intelligence claim.
