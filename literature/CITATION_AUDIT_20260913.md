# Citation audit — 2026-09-13

Scope: all 15 references and every comparative characterization in
`paper/NEUROCAD_CONTROLLED_COMPILER_PAPER.md` and `literature/RELATED_WORK.md`.
Primary author records (CVF Open Access or arXiv) were checked on 2026-09-13.
This audit verifies identity, venue/year where declared, input/output task, and
whether the manuscript's short characterization is supported by the source.
It does not claim that any cited system is a directly compatible baseline.

| # | Work | Primary record | Metadata | Characterization used by NeuroCAD | Result |
|---:|---|---|---|---|---|
| 1 | CSGNet | [CVF](https://openaccess.thecvf.com/content_cvpr_2018/html/Sharma_CSGNet_Neural_Shape_CVPR_2018_paper.html) | Sharma et al.; CVPR 2018 | Infers CSG programs from 2D/3D target shapes using execution/rendering feedback | Verified |
| 2 | ShapeAssembly | [arXiv](https://arxiv.org/abs/2009.08026) | Jones et al.; SIGGRAPH Asia 2020 | Generates executable hierarchical cuboid-assembly programs | Verified |
| 3 | SketchGraphs | [arXiv](https://arxiv.org/abs/2007.08506) | Seff et al.; 2020 | Large real-world sketch dataset represented as entity/constraint graphs | Verified |
| 4 | Fusion 360 Gallery | [arXiv](https://arxiv.org/abs/2010.02392) | Willis et al.; SIGGRAPH 2021 | Dataset/environment of human sketch-and-extrude design sequences | Verified |
| 5 | DeepCAD | [CVF](https://openaccess.thecvf.com/content/ICCV2021/html/Wu_DeepCAD_A_Deep_Generative_Network_for_Computer-Aided_Design_Models_ICCV_2021_paper.html) | Wu et al.; ICCV 2021 | Transformer generation of CAD operation sequences; no text input | Verified |
| 6 | SketchGen | [arXiv](https://arxiv.org/abs/2106.02711) | Para et al.; 2021 | Generates sketch primitives and constraints using a sequential language | Verified |
| 7 | Vitruvion | [arXiv](https://arxiv.org/abs/2109.14124) | Seff et al.; ICLR 2022 | Autoregressively generates editable parametric sketches and constraints | Verified |
| 8 | CAD-SIGNet | [CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Khan_CAD-SIGNet_CAD_Language_Inference_from_Point_Clouds_using_Layer-wise_Sketch_CVPR_2024_paper.html) | Khan et al.; CVPR 2024 | Recovers sketch/extrusion command histories from point clouds | Verified |
| 9 | Text2CAD | [arXiv](https://arxiv.org/abs/2409.17106) | Khan et al.; NeurIPS 2024 Spotlight | Maps natural-language instructions to parametric CAD sequences | Verified |
| 10 | CAD-Recode | [arXiv](https://arxiv.org/abs/2412.14042) | Rukhovich et al.; 2024 preprint | Maps point clouds to executable Python CAD code | Verified |
| 11 | CAD-MLLM | [arXiv](https://arxiv.org/abs/2411.04954) | Xu et al.; 2024 preprint, revised 2025 | Conditions CAD-sequence generation on text, images, points, or combinations | Verified |
| 12 | CAD-Llama | [CVF](https://openaccess.thecvf.com/content/CVPR2025/html/Li_CAD-Llama_Leveraging_Large_Language_Models_for_Computer-Aided_Design_Parametric_3D_CVPR_2025_paper.html) | Li et al.; CVPR 2025 | Uses an LLM and structured parametric CAD code for text-conditioned generation | Verified |
| 13 | CADCrafter | [CVF](https://openaccess.thecvf.com/content/CVPR2025/html/Chen_CADCrafter_Generating_Computer-Aided_Design_Models_from_Unconstrained_Images_CVPR_2025_paper.html) | Chen et al.; CVPR 2025 | Generates parametric CAD models from unconstrained images | Verified |
| 14 | Constraint/design-intent alignment | [CVF](https://openaccess.thecvf.com/content/ICCV2025/html/Casey_Aligning_Constraint_Generation_with_Design_Intent_in_Parametric_CAD_ICCV_2025_paper.html) | Casey et al.; ICCV 2025 | Distinguishes constraint satisfaction from alignment with design intent | Verified |
| 15 | Pointer-CAD | [CVF](https://openaccess.thecvf.com/content/CVPR2026/html/Qi_Pointer-CAD_Unifying_B-Rep_and_Command_Sequences_via_Pointer-based_Edges__CVPR_2026_paper.html) | Qi et al.; CVPR 2026 | Conditions command generation on text plus intermediate B-Rep and points to faces/edges | Verified |

## Findings and corrections

- All 15 cited works resolve to a primary author or proceedings record and are
  relevant to the related-work statements in which they appear.
- The bibliography was expanded from abbreviated labels to full titles and
  authoritative venue status where the primary record states one.
- Pointer-CAD's title was corrected to “Edges & Faces Selection.”
- CAD-MLLM now names Xu et al.; its record is described as a preprint rather
  than assigned an unsupported venue.
- Text2CAD now records its NeurIPS 2024 Spotlight status.
- No citation supports direct numerical comparison with NeuroCAD. The paper
  correctly treats these systems as adjacent work and still requires an
  executed, task-compatible strong baseline for a competitive claim.

## Claim-level disposition

The related-work claims pass for the narrow distinctions they make: input
modality, program representation, execution relationship, and constraint/design
intent. They do not support claims of NeuroCAD algorithmic novelty, superiority,
general natural-language competence, B-Rep capability, or state of the art; the
manuscript explicitly disclaims those conclusions.
