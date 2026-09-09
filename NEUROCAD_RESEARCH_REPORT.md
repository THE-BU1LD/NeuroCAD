# NeuroCAD research report

## Research question actually supported

The current system supports an engineering question: can a narrow, explicit language for common dimensioned parts be converted reproducibly into an editable program while rejecting incomplete input? It does not presently support a claim about learned machine intelligence.

## System under evaluation

NeuroCAD normalizes stated units to millimetres, constructs dimensioned primitives and subtractive features, adapts them to `neurocad-ir-v1`, validates schema/hierarchy/parameters/constraints, and deterministically emits OpenSCAD. The IR makes edit points explicit and preserves composition rather than treating generated text as the representation.

The measured criteria that genuinely apply are:

- syntactic validity;
- semantic parameter exactness on synthetic tasks;
- geometric-program validity before meshing;
- constraint satisfaction;
- exact serialization round trip;
- deterministic export;
- editable-node count, hierarchy depth, program size, and inference latency;
- optional watertightness/topology when a compiled mesh is supplied.

No metric is reported for semantic equivalence beyond the declared synthetic task signature, physical performance, BREP topology, or learned generalization.

## Benchmark design

`neurocad-benchmark-v1` contains 48 deterministically generated tasks:

- 20 train-labelled tasks: plates with holes, boxes, cylinders, spheres;
- 12 validation-labelled tasks: lexical variants, slot composition, centimetre perturbations;
- 16 test-labelled tasks: enclosures, held-out inch units, and eight examples forming four counterfactual pairs.

The labels are organizational because no training occurs. They prevent accidental conflation of familiar and held-out templates and make a future learning study easier to define. The benchmark is synthetic and overlaps the documented product grammar, so its 100% score is a regression/coverage result, not evidence of open-world generalization.

The final controlled research run adds a separate 240-task stress set with seven prompt families, 144/48/48 labelled splits, and three baselines. It also evaluates 1,000 generated typed programs, 240 predeclared malformed inputs, 200 constraint corruptions, 200 automated parameter edits, all 240 real OpenSCAD/STL kernel cases, and hierarchy depth through the enforced limit. These use new `NC-EXP-001` through `NC-EXP-007` identifiers and do not reinterpret historical experiments.

## Baselines and result

| System | Semantic exact | Intervention consistency |
|---|---:|---:|
| NeuroCAD | 48/48 (100%) | 4/4 (100%) |
| Raw numbers, no unit normalization | 18/48 (37.5%) | 1/4 (25%) |
| Fixed 80 mm box | 0/48 (0%) | 0/4 (0%) |

On NC-EXP-001, NeuroCAD scored 240/240; train-set nearest-neighbor retrieval scored 144/240, raw-number extraction scored 110/240, and fixed output scored 0/240. All discordant pairs favored NeuroCAD (exact two-sided McNemar p-values 2.52e-29, 1.47e-39, and 1.13e-72 respectively). These are controlled-generator comparisons, not evidence against contemporary trained CAD models.

NC-EXP-002 passed 1,000/1,000 typed programs. NC-EXP-003 rejected 240/240 malformed cases. Declared constraints detected 200/200 parameter corruptions versus 0/200 without constraints; automated edits succeeded in 200/200 cases. OpenSCAD compiled 240/240 benchmark programs into STL that passed topology, connectivity, volume, finite-value, and expected-extents verification. Wilson intervals and all raw records are in the expanded run.

The unit-normalization ablation performs notably worse on validation and held-out units. The fixed baseline establishes that benchmark fields are not satisfied by a constant default. These are deterministic program comparisons; no statistical inference is warranted.

## Historical negative result

The historical typed-parser causal/mechanism claim remains falsified. The current canonical IR is a new engineering implementation and cannot be used to reinterpret that result.

The VeriCodeGen Stage 1 receipt demonstrates only that a scripted six-cell plumbing path ran. It made no language-model calls. Stage 2 remains blocked without authorization and Stage 3 has not run. Therefore there is no present evidence that NeuroCAD improves model reasoning, code generation, or geometric generalization.

## Threats to validity

- Tasks are synthetic and generated from the supported grammar.
- Expected signatures are deliberately narrower than full geometric equivalence.
- No independent external CAD kernel checked every benchmark output.
- No learning system, OOD dataset, human CAD corpus, or blinded evaluator was used.
- Timing is local and intended for regression diagnosis, not cross-system performance claims.
- At the time of this historical report the checkout lacked Git metadata. A later
  audit initialized local history, but it does not recover the missing original
  provenance or provide a published exact-revision receipt.

## Conservative conclusion

NeuroCAD now has credible software evidence and a complete controlled engineering manuscript for a small editable prompt-to-CAD compiler. It does not have evidence for general machine intelligence or learned CAD reasoning. A learned successor study still requires a compatible frozen external corpus, independently audited verification, predeclared multi-seed analysis, authorized model execution, and retained failures.
