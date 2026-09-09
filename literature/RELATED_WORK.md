# Related work

CAD program synthesis spans inverse graphics, program induction, parametric sequence modeling, and executable code generation. CSGNet learns compact constructive-solid-geometry programs from target shapes, while ShapeAssembly uses a part-assembly DSL. These establish that execution-aware program representations matter, but neither addresses NeuroCAD's bounded dimensioned-language compiler contract.

Parametric datasets and learned representations are substantially richer than this project. SketchGraphs supplies large constraint graphs; Fusion 360 Gallery captures human sketch/extrude histories; DeepCAD models sketch/extrusion command sequences. SketchGen and Vitruvion learn sketch entities and constraints. Their scale and output languages make them suitable for learned generation questions, not direct baselines for a deterministic plate/enclosure compiler.

Recent systems broaden inference: CAD-SIGNet and CAD-Recode reconstruct programs from point clouds; Text2CAD and CAD-Llama map language to parametric command sequences; CADCrafter uses images; CAD-MLLM uses multiple modalities. Work on aligning constraints with design intent highlights that constraint satisfaction does not by itself establish intent recovery. Pointer-CAD further unifies B-Rep and command-sequence structure. NeuroCAD does not claim parity with any of these.

The defensible contribution here is evaluation discipline around a small executable compiler: canonical typed IR, fail-closed staged validation, exact controlled semantics, retained negative evidence, actual kernel sampling, and a one-command evidence bundle. These ideas are standard compiler/reproducibility practice applied carefully; scientific algorithmic novelty is not claimed.

Full links and task distinctions are in `literature_matrix.csv`.

