# Qualitative result selection

Selection was fixed as the first eight task IDs before outcomes were inspected. Machine-readable input, ground truth, every system prediction, and pass/fail state are in `research/runs/NC-RUN-2026-09-03-FULL/analysis/qualitative_predeclared.json`.

Actual OpenSCAD renders are under `figures/kernel_examples/`. They cover box, cylinder, enclosure, holed plate, plain plate, slotted plate, and sphere before repeating families. Each render has adjacent canonical IR, SCAD, STL, and mesh-validation JSON under `generated/kernel/`.

The controlled NeuroCAD examples contain no semantic failures. To prevent a success-only gallery, baseline failures and invalid-input failures are presented in the JSON records and error taxonomy. The nearest-neighbor system fails every validation/test task because it copies training parameters; raw-number parsing fails structured features and unit shifts; fixed output fails all tasks. Invalid examples show explicit parser/validator messages rather than a fabricated render.
