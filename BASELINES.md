# Baselines and comparison fairness

NC-EXP-001 evaluates five systems on identical task records and exact semantic signatures:

1. **NeuroCAD:** the supported compiler.
2. **Nearest-neighbor retrieval:** token-set Jaccard retrieval over train-labelled prompts, returning the nearest training label unchanged. It receives task labels only for the training split.
3. **Normalized dimensions only:** normalizes dimensions/units while omitting the full typed-feature pipeline; this ablation is present in `core/benchmark.py` and the retained five-system study.
4. **Raw numbers/no unit normalization:** extracts literal numbers and emits a primitive signature without unit conversion or structured features.
5. **Fixed box:** always returns an 80 mm cube.

All are deterministic and run locally on CPU. Parameter- and compute-matching are not meaningful because no learned model is proposed. Directly comparing these retained scores to DeepCAD, Text2CAD, CAD-Llama, CAD-Recode, or other learned-system scores would be invalid: they solve different input/output tasks, use large external corpora, and target richer sketch/extrusion sequences. The literature matrix records them as neighboring work, not measured competitors.


A prospective comparison on an explicitly matched task is possible. It requires frozen input/output adapters, model revisions, licenses, budgets, independent cases and the same scorer. The old study is not reopened. See [the verified-intent upgrade plan](docs/VERIFIED_INTENT_UPGRADE_PLAN_20261014.md).
