# Baselines and comparison fairness

NC-EXP-001 evaluates four systems on identical task records and exact semantic signatures:

1. **NeuroCAD:** the supported compiler.
2. **Nearest-neighbor retrieval:** token-set Jaccard retrieval over train-labelled prompts, returning the nearest training label unchanged. It receives task labels only for the training split.
3. **Raw numbers/no unit normalization:** extracts literal numbers and emits a primitive signature without unit conversion or structured features.
4. **Fixed box:** always returns an 80 mm cube.

All are deterministic and run locally on CPU. Parameter- and compute-matching are not meaningful because no learned model is proposed. Comparisons to DeepCAD, Text2CAD, CAD-Llama, CAD-Recode, or other learned systems would be invalid: they solve different input/output tasks, use large external corpora, and target richer sketch/extrusion sequences. The literature matrix records them as neighboring work, not measured competitors.

