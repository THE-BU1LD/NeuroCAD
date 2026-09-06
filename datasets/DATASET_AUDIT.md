# Dataset audit

## Dataset used

`compiler_stress_v1.jsonl` is generated deterministically by `core/research_suite.py` with seed 20260902. It contains 240 unique prompts balanced by round-robin family assignment across plate, holes, slots, enclosure, box, cylinder, and sphere. Index modulo ten fixes 60% train, 20% validation, and 20% test labels. Test-labelled cases introduce centimetre/inch expressions and lexical variants; no system tuning occurs after outcome inspection. Exact bytes and SHA-256 are frozen in the run manifest.

The set is CC0-equivalent project-authored synthetic data under this repository's MIT release. It contains no people or private data. Leakage risk is structural: generation templates overlap the declared grammar. Accordingly, scores measure contract coverage and controlled compositional/unit shifts, not open-world language generalization.

`ir_programs.jsonl` contains 1,000 seed-generated typed programs spanning six primitives, three Boolean compositions, transforms, parameters, references, and dimension constraints. `invalid_cases.jsonl` contains 240 predeclared malformed cases over eight categories. These are test generators, not natural CAD corpora.

## External dataset suitability

| Dataset | Useful content | License/scale concern | Decision |
|---|---|---|---|
| DeepCAD | 178,238 Onshape-derived sketch/extrude sequences | Representation and task differ; full corpus/kernel conversion is not present in this checkout | Not used; would require a learned sequence study |
| SketchGraphs | 15M constraint graphs, with filtered official splits | Raw data are tens of GB and original sketch copyrights/Onshape terms require care | Not used; NeuroCAD does not solve 2D sketches |
| Fusion 360 Gallery | 8,625 human design sequences | Non-commercial research license and no redistribution of the full dataset | Not used; Fusion sketch/extrude language is not `neurocad-ir-v1` |

No external benchmark result is claimed. This is preferable to a lossy conversion whose reliability, duplication, and kernel equivalence cannot be audited in the current task.

## Quality checks

- exact prompt uniqueness is enforced during generation;
- seed and generator version are stored;
- every task stores expected structured semantics, not rendered-image labels;
- no failed result is removed;
- split membership is deterministic before evaluation;
- conversion to IR is evaluated by exact declared fields, while OpenSCAD execution is separately sampled;
- unsupported semantic equivalence, BREP identity, and human quality are not inferred.

