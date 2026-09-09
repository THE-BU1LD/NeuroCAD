# Reviewer 2 — theory/method

## Summary
The method is a partial deterministic compiler with typed CSG IR and explicit validation. Its mathematical behavior is straightforward and now specified accurately.

## Strengths
Clear partial-function contract, explicit units, bounded graph semantics, deterministic serialization, and separation of constraints from solving.

## Weaknesses and fatal concern
There is no novel learning or geometry algorithm. The main result cannot establish broad language-to-CAD capability because the evaluator and generator share the same narrow contract.

## Major concerns
Constraint ablation only demonstrates declared equality checking; semantic signatures are narrower than full geometric equivalence; OpenSCAD mesh checks do not establish BREP topology or manufacturability.

## Minor concerns
Complexity is characterized asymptotically only; kernel numerical conditioning is not studied.

## Missing experiments
Independent semantics, geometry equivalence beyond extents/topology, controlled perturbation boundaries, and stronger representation comparison.

## Assessment
Novelty: **engineering integration only**. Reproducibility: good for current code. Likely score: **2/10 reject** at NeurIPS/ICML; potentially suitable as a reproducibility/systems case study after new evidence. Confidence: **5/5**.

## Post-audit disposition
The manuscript and novelty audit now disclaim algorithmic novelty. The concern remains by design rather than being hidden with added complexity.
