# NeuroCAD S3 Benchmark Taxonomy — Candidate Pool v0

Status: **PRE-FREEZE / CANDIDATE_ONLY / NOT_EVALUATED**

This artifact exists to build the candidate universe before selecting or scoring a held-out benchmark. It is not a benchmark result, not a finalized test set, and not authorization to evaluate any system.

## Scientific boundary

- No candidate in `benchmark_candidate_pool_v0.csv` has been scored by NeuroCAD or any baseline for S3 selection.
- Do not use model outcomes to decide which candidates survive deduplication, balancing, or final selection.
- The historical typed-parser-specific mechanism remains falsified / validation-dominant; this pool does not revise that result.
- Final benchmark composition, baseline identities, provider/model versions, validation policy, metrics, seeds, thresholds, hypotheses, ablations, and execution authorization must be frozen separately before held-out evaluation.
- Synthetic authoring provenance is explicit. External benchmark adapters must be added as separate provenance classes rather than relabeling these prompts as external data.

## Candidate taxonomy

1. `primitive_solids` — single-part basic constructive geometry with explicit dimensions.
2. `dimensional_edits` — localized dimension/position changes where unaffected constraints should remain stable.
3. `bores_cutouts` — subtractive features: through/blind holes, slots, pockets, notches, bores.
4. `patterns` — linear, circular, mirrored, grid, repeated-feature construction.
5. `fillets_chamfers` — edge-treatment scope and radius/distance interpretation.
6. `assemblies_compositions` — multi-part or multi-body composition and mating relationships.
7. `ambiguous_constraints` — underspecified but plausible user requests where a system should expose/resolve assumptions rather than hallucinate certainty.
8. `invalid_underspecified` — impossible, contradictory, missing-reference, or physically inconsistent requests; expected behavior may be rejection/clarification rather than geometry.
9. `multi_step_edits` — ordered sequences that test state preservation across multiple edits.
10. `constraint_interactions` — multiple simultaneous constraints where satisfying one can violate another.
11. `reference_frame_language` — relational/spatial language such as left/right/front/back, mid-plane, viewed-from, nearest edge, alignment.

Current candidate count: **110** (10 per taxonomy class).

## Pre-freeze selection rules

These rules must be applied without inspecting model outcomes:

- Deduplicate semantically equivalent prompts before final split assignment.
- Preserve all 11 taxonomy classes in the final candidate accounting.
- Record every deletion with reason: `DUPLICATE`, `AMBIGUITY_POLICY`, `UNIMPLEMENTABLE_REFERENCE`, `OUT_OF_SCOPE`, or another predeclared non-outcome reason.
- If a prompt needs a prior model state, bind it to a deterministic reference fixture before evaluation.
- Keep invalid/underspecified prompts in a separate response-policy stratum; do not grade refusal/clarification prompts as if geometry must always be produced.
- Freeze units and coordinate/view conventions in the protocol.
- Do not alter wording after any held-out system output has been inspected, except through a new versioned benchmark.
- Final held-out selection must be committed with a checksum and authorization manifest before outcome access.

## Required next artifacts

- external benchmark adapter A with exact source/license/provenance;
- external benchmark adapter B with exact source/license/provenance;
- deterministic reference fixtures for stateful/edit prompts;
- deduplication + inclusion/exclusion ledger;
- final split manifest;
- exact system/baseline/provider identities;
- H1/H2/H3 and mechanism-ablation specification;
- metric/error taxonomy;
- execution authorization manifest/hash.

Issue: `THE-BU1LD/NeuroCAD#36`.
