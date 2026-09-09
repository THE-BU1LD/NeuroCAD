# NeuroCAD: An Executable, Fail-Closed Evaluation of a Controlled Text-to-CAD Compiler

## Abstract

Text-to-CAD systems are easy to overstate when syntactically plausible output or a small render gallery substitutes for executable validation. We examine a retained NeuroCAD controlled run of a deliberately bounded deterministic compiler, not a learned general-purpose CAD model. The studied system maps fully dimensioned English requests for plates, rectangular boxes and open-top enclosures, cylinders, spheres, circular holes, and rectangular slots into a typed JSON program, validates structure/references/parameters/constraints, emits deterministic OpenSCAD, and optionally executes the result to STL. On a frozen 240-task synthetic contract test, it recorded 240/240 exact semantic matches, versus 144/240 for train-set nearest-neighbor retrieval, 110/240 for raw-number extraction without unit normalization, and 0/240 for a fixed output. Across 1,000 generated typed programs, 1,000/1,000 passed static validity, declared constraints, exact serialization round trip, and deterministic export (Wilson 95% interval 99.62–100%). The run also records complete rejection of its generated malformed-input fixtures, 200/200 injected parameter drifts detected with declared constraints versus 0/200 after constraint removal, 200/200 automated parameter edits surviving validation and export, and 240/240 benchmark programs compiling with OpenSCAD to STL under the retained topology/extents checks. The frozen manifest lacks a source revision or source-tree digest, so these are claims about the retained historical run rather than proof for the current a6 source candidate. They do not establish natural-language generalization, design-intent inference, BREP reconstruction, manufacturability, or algorithmic novelty. A historical typed-parser mechanism claim remains explicitly falsified.

## 1. Introduction

Parametric CAD is executable structure: operations, references, parameters, constraints, and geometry-kernel behavior matter. A generated string can be grammatically valid while referencing absent entities, violating constraints, producing an empty mesh, or expressing the wrong part. Research evaluation must therefore separate syntax, typed program validity, semantic correctness, execution, and solid validity.

NeuroCAD began as a repository containing several incompatible experimental paths and claims stronger than their evidence. In particular, the repository's own successor protocol records the historical claim that a typed parser improved model behavior as falsified. Rather than hide that result or describe disconnected neural modules as a complete system, this work narrows the supported object: a deterministic compiler for an explicit dimensioned-language subset.

The engineering contributions are:

1. a versioned typed CAD program with formal machine schema, references, transforms, hierarchy, Boolean composition, declared constraints, deterministic serialization, and exact round trips;
2. a fail-closed staged parser/compiler with bounded input and explicit error categories;
3. a frozen evaluation that retains every per-example baseline prediction and failure, separates static validation from real OpenSCAD/STL execution, and reports paired comparisons and uncertainty;
4. a one-command evidence package with configs, hashes, generated programs, kernel artifacts, renders, logs, metrics, figures, tests, and a claim ledger;
5. an integrity ledger that prevents repaired 2026 software from being misrepresented as evidence for historical experiments.

We do not claim a new learning algorithm, a state-of-the-art result, or open-world text-to-CAD.

## 2. Related Work

CSGNet [1] learns constructive-solid-geometry programs from target shapes, and ShapeAssembly [2] represents shapes with executable part-assembly programs. These works motivate explicit executable structure but address inverse graphics rather than a controlled text compiler.

Large parametric CAD corpora support richer learned tasks. SketchGraphs [3] provides geometric constraint graphs from millions of CAD sketches. Fusion 360 Gallery [4] contains human sketch/extrude construction sequences and a programmatic reconstruction environment. DeepCAD [5] models CAD construction sequences derived from Onshape documents. SketchGen [6] and Vitruvion [7] generate sketch entities and constraints. These datasets and systems use representations not directly compatible with `neurocad-ir-v1`.

Recent reconstruction and multimodal work includes CAD-SIGNet from point clouds [8], Text2CAD from language [9], CAD-Recode as executable CadQuery code generation [10], CAD-MLLM across multiple modalities [11], CAD-Llama for language-conditioned parametric sequences [12], and CADCrafter from images [13]. Constraint/design-intent alignment work [14] underscores that satisfying constraints does not imply recovering designer intent. Pointer-CAD [15] moves toward unifying B-Rep and command sequences. These are neighboring systems, not measured baselines: direct scores would confound task, data, representation, geometry kernel, model scale, and compute.

Our novelty audit finds no new CAD algorithm. The contribution is a reproducible engineering and evidence standard for a narrow executable contract.

## 3. Problem Formulation

Let \(x\) be a string in a declared language \(L\), and let \(y\) be its task signature: primitive kind, dimensions, feature counts and dimensions, and enclosure state where applicable. A deterministic compiler \(C\) produces program \(p=C(x)\), or rejects \(x\) with explicit errors. A static validator \(V(p)\) checks schema, types, references, hierarchy, parameter domains, and declared constraints. A serializer \(S\) and parser \(P\) satisfy exact round-trip identity when \(P(S(p))=p\). Exporter \(E(p)\) emits OpenSCAD. For the executed sample, kernel \(K(E(p))\) emits an STL mesh \(m\), and mesh verifier \(M(m)\) checks non-emptiness, positive three-dimensional extents, and watertightness.

Semantic exactness is \(I[\sigma(p)=y]\), where \(\sigma\) extracts only predeclared task fields. This is stricter than syntax but narrower than arbitrary geometric equivalence. The primary hypothesis is paired superiority in semantic exactness over fixed, raw-number, and retrieval baselines on the frozen task set. Acceptance criteria for controlled static, invalid-input, edit, and executed-kernel suites were fixed at 100% because any failure is actionable compiler evidence.

## 4. Representation

The canonical program declares version `neurocad-ir-v1` and millimetre units. Nodes are uniquely identified primitive leaves or Boolean compositions. Supported leaves are box, rounded box, sphere, cylinder, cone, and torus; supported compositions are union, difference, and intersection. Every node has translation, XYZ rotation, scale, and a role. Programs designate roots and may declare dimension, coincident, offset, child-count, or bounds constraints.

The normative Draft 2020-12 JSON Schema rejects unknown or mistyped fields. Semantic validation resolves references, rejects duplicate IDs and multiple parents, checks acyclicity, limits the graph to 1,024 nodes and depth 128, verifies finite primitive-specific parameter domains and non-zero scale, and evaluates constraints. Deterministic JSON serialization uses stable key ordering. OpenSCAD export preserves the explicit operation tree.

## 5. Method

The prompt frontend normalizes text and parses either three-dimensional sequences (`x`, `×`, or `by`) or named dimensions. Millimetres, centimetres, metres, `in`, `inch`, and `inches` normalize to millimetres. Fully dimensioned plate, box, enclosure, cylinder, and sphere templates are accepted. Holes require diameter and slots require two dimensions. Feature counts are bounded. Missing required dimensions and unsupported domains yield semantic-input errors; no default geometry is approved for fabrication.

The parsed compatibility graph is immediately adapted to canonical IR. The compiler then runs schema/type checks, reference resolution, hierarchy checks, parameter/transform checks, constraint checks, deterministic serialization, and OpenSCAD export. Structured input is capped at 1 MiB and depth/node limits prevent recursive exhaustion. Kernel execution uses a fixed OpenSCAD argument vector, a timeout, non-empty artifact checks, and independent `trimesh` loading/watertightness checks.

## 6. Training

There is no proposed learned model and no training. Consequently, parameter count, FLOPs, optimizer, checkpoint selection, and training seeds are not applicable. The retrieval baseline indexes only train-labelled controlled prompts using token-set Jaccard similarity and copies the nearest expected signature. It is an evaluation comparator, not a NeuroCAD component.

## 7. Experimental Setup

Run `NC-RUN-2026-09-03-FULL` uses seed 20260902. NC-EXP-001 contains 240 unique generated tasks distributed deterministically as 144 train, 48 validation, and 48 test. Families rotate among plate, holes, slots, enclosure, box, cylinder, and sphere. Validation/test templates change lexical form and units. Because prompts are generated from the contract, this is regression and controlled-shift evidence, not a natural-language sample.

NC-EXP-002 generates 1,000 IR programs across six primitives, transforms, three Boolean compositions, references, and dimension constraints. NC-EXP-003 generates 240 invalid cases, 30 each for malformed syntax, wrong type, absent reference, inconsistent constraint, non-finite value, duplicate ID, cycle, and incomplete semantic prompt. NC-EXP-004 injects 200 one-millimetre parameter corruptions with and without a matching declared dimension constraint. NC-EXP-005 performs 200 named box-width edits. NC-EXP-006 chooses all 240 tasks in sorted-family round-robin order and compiles them using OpenSCAD 2021.01 with `$fn=48`; selection precedes outcomes. NC-EXP-007 constructs hierarchy depths 1–129.

Binomial rates include two-sided 95% Wilson intervals. Per-task baseline comparisons use exact two-sided McNemar tests, reporting discordant counts. Timings are local diagnostics, not portable performance claims.

## 8. Datasets and Baselines

The controlled JSONL and generated IR data are project-authored and hashed in the run manifest. Their generator is deterministic under a fixed implementation, but the historical manifest does not identify that implementation by source digest or commit; exact source-level reproduction therefore remains unproven. Exact duplicate prompts are prohibited. DeepCAD, SketchGraphs, and Fusion 360 Gallery were audited but not used because NeuroCAD neither trains a sequence model nor consumes their sketch/extrude/constraint representations. Forcing a lossy conversion without an audited kernel mapping would weaken validity.

Baselines are: an 80 mm fixed cube; literal-number extraction without unit normalization or structured feature parsing; and nearest-neighbor retrieval over train-labelled tasks. They establish constant-output, surface-token, and memorization reference points. Parameter/compute matching is inapplicable without learned models.

## 9. Main Results

| System | Train | Validation | Test | Overall |
|---|---:|---:|---:|---:|
| NeuroCAD | 144/144 | 48/48 | 48/48 | 240/240 (100%) |
| Nearest-neighbor retrieval | 144/144 | 0/48 | 0/48 | 144/240 (60.0%) |
| Raw numbers/no unit normalization | 82/144 | 28/48 | 0/48 | 110/240 (45.8%) |
| Fixed box | 0/144 | 0/48 | 0/48 | 0/240 (0%) |

Against retrieval, 96 pairs were discordant and all favored NeuroCAD (exact two-sided McNemar \(p=2.52\times10^{-29}\)). Against raw numbers, 130/130 discordant pairs favored NeuroCAD (\(p=1.47\times10^{-39}\)); against fixed output, 240/240 favored NeuroCAD (\(p=1.13\times10^{-72}\)). These p-values describe the frozen controlled set and do not convert it into a random natural-language sample.

NC-EXP-002 passed 1,000/1,000 programs, with Wilson interval 99.62–100%. The earlier draft's timing values were not sourced from the named FULL run and are withdrawn. New runs retain host-load-dependent timing and memory observations in a runtime receipt while excluding them from the deterministic scientific digest.

## 10. Validity Analysis

NC-EXP-003 rejected all 240 retained malformed-fixture records, but these are eight distinct templates repeated 30 times. They establish regression coverage for those eight categories only; the earlier 240-case Wilson interval is withdrawn because the records are not independent samples. The hardened future runner generates and hashes a unique variant for every record and still treats the outcome as deterministic regression evidence rather than a population estimate. NC-EXP-006 separately compiled 240 unique benchmark programs to STL passing topology and expected-extents checks (Wilson 98.42–100%). Complete success on this controlled set does not establish universal geometry validity.

Compiled families included boxes, cylinders, open-top enclosures, plates, holed plates, slotted plates, and a sphere. Mesh artifacts include canonical IR, SCAD source, STL, render, extents, volume, vertex/face counts, and validation JSON. Static success is never substituted for these kernel results.

## 11. Ablations

In NC-EXP-004, constraints detected 200/200 injected parameter drifts. Removing only the constraint yielded 0/200 detections because the corrupted primitive remained valid in isolation. This supports the narrow claim that declared equality constraints detect drift. It does not establish intent inference, a numerical constraint solver, or a learned causal mechanism.

The raw-number comparator functions as a frontend ablation: removing unit normalization and structured feature parsing reduced exactness from 240/240 to 110/240, including 0/48 test cases. Because several capabilities are removed together, the result does not isolate a single causal component.

## 12. Generalization and Stress Tests

Nearest-neighbor retrieval's 144/144 train score and 0/96 validation/test score expose memorization under changed parameters/templates. NeuroCAD's 96/96 controlled held-out-label score shows rule execution across those predesigned shifts. It is not OOD evidence beyond the grammar.

NC-EXP-007 validated/exported constructed trees through depth 128 (255 nodes, 88,102 SCAD bytes at depth 128) and rejected depth 129 with explicit `hierarchy_too_deep` rather than recursing indefinitely. The suite also covers transforms, near-small positive dimensions, all six IR primitives, all three Boolean operators, invalid inputs, and unit precision. It does not cover sketch constraints, fillets, BREP topology, symmetry inference, or adversarial numerical kernels.

## 13. Error Analysis

NeuroCAD had no failures on the controlled valid tasks. This should be interpreted as a contract test result. Baseline semantic mismatches were 96/240 retrieval, 130/240 raw-number, and 240/240 fixed. Retrieval copied incorrect parameters outside training; raw-number extraction missed features and unit conversion; fixed output never matched. Invalid input yielded explicit messages rather than generated fallbacks.

Kernel failure, empty/non-volume meshes, inconsistent winding, disconnected bodies, and dimension mismatches occurred 0/240 in the executed benchmark. Self-intersection beyond the volume/manifold checks and exact BREP topology were not measured. All per-example outputs, including baseline failures, are retained rather than summarized away.

## 14. Qualitative Results

The qualitative set is the first eight task IDs, selected before outcome inspection. Its machine-readable record contains input, ground truth, prediction, and pass/fail for every system. All 240 kernel examples use the predeclared deterministic selection and include actual OpenSCAD PNG renders with IR/SCAD/STL/validation neighbors. Baseline and invalid-input failures are included in the records and taxonomy, preventing a success-only gallery.

## 15. Practical Editability

NC-EXP-005 changed a named box-width parameter, then validated, serialized, reparsed, and exported each result. All 200/200 edits succeeded (Wilson 98.12–100%), with mean local pipeline time 1.78 ms. This is machine editability, not evidence that designers find the representation usable. A human protocol is specified but explicitly unexecuted.

## 16. Reproducibility

`scripts/reproduce_research.sh` requires CPython 3.12.14, creates a fresh isolated environment and a new output directory, installs the exact package lock, runs maintained quality gates, executes every required kernel sample with reuse disabled, regenerates JSONL/programs/STL/renders/metrics/figures, builds fresh distributions, and smoke-tests the exact wheel. New manifests record maintained-source and lock digests, package version, Git state when available, Python/dependency identity, and OpenSCAD version. Deterministic outcome hashes are separated from timing/runtime receipts. OpenSCAD remains an external requirement.

This checkout now has a local audit Git history, but that history was initialized
after the original repository history was unavailable and is not published on the
configured canonical remote. The frozen run manifest is not bound to its producing
source revision or an a6 distribution, and 181 of its 240 kernel records were
accepted from already present artifacts. The retained run is therefore historical
development evidence, not a fresh confirmatory reproduction of the current source.
An archival release must run the non-resuming protocol from a clean published
revision and retain source/lock/kernel provenance, commit/tag state, CI URL, exact
distribution hashes, and anonymous installer evidence.

## 17. Limitations

The language is small, template-like, English-only, and generated evaluation data overlap its rules. No standard external CAD benchmark is directly evaluated. Expected signatures do not prove full geometric equivalence. All 240 controlled tasks use the geometry kernel, but OpenSCAD CSG/STL is not BREP/STEP and cannot establish exact CAD topology. No constraint solver, sketch language, fillet, thread, tolerance, material, load, simulation, manufacturability, or safety analysis exists. No learned model, human study, external replication, or public-release provenance exists. Historical neural modules are not part of the supported system.

## 18. Ethics and Impact

The controlled datasets contain no personal data. The principal risk is automation overtrust: a valid mesh may still be unsafe or unmanufacturable. NeuroCAD labels itself an alpha design aid, fails closed on unsupported prompts, and explicitly requires qualified review before fabrication. It must not be used as sole authority for medical, vehicle, structural, aerospace, or other safety-critical components.

## 19. Conclusion

The retained run shows that a small text-to-CAD compiler was executable on its frozen controlled suite, exceeded three simple baselines, and produced kernel artifacts under the stated checks. Its original manifest lacks source-revision provenance, so it does not prove that current source reproduces those outcomes. The hardened runner now creates source-bound, non-resumed evidence for a future exact revision. Neither the historical run nor this engineering work demonstrates general CAD intelligence or a new learning mechanism. The next defensible research step is a new, frozen task with a compatible real-world corpus, stronger representation and kernel, learned and compute-matched baselines, multi-seed training, and independent replication.

## References

1. Sharma et al. “CSGNet: Neural Shape Parser for Constructive Solid Geometry.” CVPR 2018. https://openaccess.thecvf.com/content_cvpr_2018/html/Sharma_CSGNet_Neural_Shape_CVPR_2018_paper.html
2. Jones et al. “ShapeAssembly: Learning to Generate Programs for 3D Shape Structure Synthesis.” 2020. https://arxiv.org/abs/2009.08026
3. Seff et al. “SketchGraphs.” 2020. https://arxiv.org/abs/2007.08506
4. Willis et al. “Fusion 360 Gallery.” ACM TOG 2021. https://arxiv.org/abs/2010.02392
5. Wu et al. “DeepCAD.” ICCV 2021. https://openaccess.thecvf.com/content/ICCV2021/html/Wu_DeepCAD_A_Deep_Generative_Network_for_Computer-Aided_Design_Models_ICCV_2021_paper.html
6. Para et al. “SketchGen.” 2021. https://arxiv.org/abs/2106.02711
7. Seff et al. “Vitruvion.” ICLR 2022. https://arxiv.org/abs/2109.14124
8. Khan et al. “CAD-SIGNet.” CVPR 2024. https://openaccess.thecvf.com/content/CVPR2024/papers/Khan_CAD-SIGNet_CAD_Language_Inference_from_Point_Clouds_using_Layer-wise_Sketch_CVPR_2024_paper.pdf
9. Khan et al. “Text2CAD.” 2024. https://arxiv.org/abs/2409.17106
10. Rukhovich et al. “CAD-Recode.” 2024. https://arxiv.org/abs/2412.14042
11. “CAD-MLLM.” 2024. https://arxiv.org/abs/2411.04954
12. Li et al. “CAD-Llama.” CVPR 2025. https://openaccess.thecvf.com/content/CVPR2025/html/Li_CAD-Llama_Leveraging_Large_Language_Models_for_Computer-Aided_Design_Parametric_3D_CVPR_2025_paper.html
13. Chen et al. “CADCrafter.” CVPR 2025. https://openaccess.thecvf.com/content/CVPR2025/html/Chen_CADCrafter_Generating_Computer-Aided_Design_Models_from_Unconstrained_Images_CVPR_2025_paper.html
14. Casey et al. “Aligning Constraint Generation with Design Intent in Parametric CAD.” ICCV 2025. https://openaccess.thecvf.com/content/ICCV2025/html/Casey_Aligning_Constraint_Generation_with_Design_Intent_in_Parametric_CAD_ICCV_2025_paper.html
15. Qi et al. “Pointer-CAD.” CVPR 2026. https://openaccess.thecvf.com/content/CVPR2026/html/Qi_Pointer-CAD_Unifying_B-Rep_and_Command_Sequences_via_Pointer-based_Edges__CVPR_2026_paper.html

## Appendix A. Experiment map

- NC-EXP-001: controlled compiler matrix and paired baseline tests.
- NC-EXP-002: 1,000-program IR validity/round-trip/export stress.
- NC-EXP-003: malformed-input taxonomy.
- NC-EXP-004: declared-constraint corruption ablation.
- NC-EXP-005: automated parameter editability.
- NC-EXP-006: OpenSCAD execution, STL topology verification, and renders.
- NC-EXP-007: hierarchy complexity and enforced bound.

## Appendix B. Exact reproduction

From the repository root with native OpenSCAD available:

```bash
./scripts/reproduce_research.sh
```

The script creates a new `NC-REPRO-*` directory and never modifies `research/runs/NC-RUN-2026-09-03-FULL`. The latter remains the historical canonical metrics bundle; its sibling manifest holds snapshot hashes and experiment identifiers but lacks source-revision provenance.
