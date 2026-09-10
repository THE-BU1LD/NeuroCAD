# Historical VertexED → NeuroCAD provenance

This document records the bounded repository handoff tracked by NeuroCAD issue #44 without copying or rewriting historical evidence. It does not by itself close the remaining outside-subtree completeness review. The machine-readable source of truth is the provenance-manifest set plus bounded completeness inventories:

- [`vertexed_neurocad_provenance_v1.json`](vertexed_neurocad_provenance_v1.json) — core product, release, claim, Project 2424, and pilot surfaces;
- [`vertexed_neurocad_research_provenance_extension_v1.json`](vertexed_neurocad_research_provenance_extension_v1.json) — benchmark/evaluator/OOD, frozen diagnostic, successor-S3, and additional Project 2424 surfaces referenced by the historical evidence ledger;
- [`vertexed_neurocad_product_qa_provenance_extension_v1.json`](vertexed_neurocad_product_qa_provenance_extension_v1.json) — the two generated NeuroCAD Alpha product-QA artifacts recovered after the initial map, retained as `HISTORICAL_ONLY` / `INTENTIONALLY_NOT_MIGRATED` and explicitly not upgraded into scientific or held-out benchmark evidence;
- [`vertexed_neurocad_ood_provenance_extension_v1.json`](vertexed_neurocad_ood_provenance_extension_v1.json) — the late-recovered historical OOD workflow and repository-level OOD contract test, both kept historical-only and non-authorizing;
- [`vertexed_neurocad_source_inventory_v1.json`](vertexed_neurocad_source_inventory_v1.json) — the complete 48-blob inventory of the frozen `portfolio/project2424/projects/T2424-0037` subtree, bound to source tree `f741417e9710c3044044465bfeabc7a3cf185ca0` and the immutable VertexED snapshot below;
- [`vertexed_neurocad_workflow_inventory_v1.json`](vertexed_neurocad_workflow_inventory_v1.json) — the exact five `.github/workflows` entries whose basenames contain `neurocad` at the frozen source snapshot, with immutable Git blob identities and provenance owners;
- [`vertexed_neurocad_release_surface_inventory_v1.json`](vertexed_neurocad_release_surface_inventory_v1.json) — the exact six outside-subtree scripts/tests/e2e files directly referenced by the historical NeuroCAD Alpha browser, OpenSCAD, and public-CDN workflows.

## Pinned historical source

The audited baseline retired three old current-owner paths. Resolve those paths
using [`vertexed_neurocad_current_owners_v1.json`](vertexed_neurocad_current_owners_v1.json).
This separate mapping leaves every historical manifest, frozen inventory, source
commit and blob identity unchanged. It identifies present maintainers of the
contracts, not equivalent implementations or new scientific evidence.

- Repository: `vertex-studyAI/vertexED.ai`
- Snapshot: `9efb041d3d56e0dc617f5808576beff696d08a69`
- Frozen Project 2424 NeuroCAD subtree: `portfolio/project2424/projects/T2424-0037`
- Frozen subtree tree SHA: `f741417e9710c3044044465bfeabc7a3cf185ca0`
- Frozen repository root tree SHA: `c5aeb156a9c09f0408dfa3dd20bd770076b5ee76`
- Historical migration tracker: `vertex-studyAI/vertexED.ai#491`
- Canonical owner: `THE-BU1LD/NeuroCAD`

Every manifest row is pinned to that source snapshot. Where a blob or directory-tree SHA was directly recovered, it is recorded as `source_blob` or `source_tree`; otherwise the immutable commit plus path remains the provenance identity. The research extension also records later-recovered blob identities for rows already present in the core manifest, without duplicating or mutating those rows. The product-QA and OOD extensions record exact late-recovered blob identities without changing the original evidence class or authorization state.

The source inventory adds a separate completeness control for the embedded Project 2424 NeuroCAD subtree. It records all 48 blobs and their exact Git blob identities under the frozen tree SHA. Its regression checksum means deleting, adding, renaming, or changing a recorded blob identity fails deterministically. The workflow inventory independently enumerates all five explicitly NeuroCAD-named workflows at the frozen repository root tree, and the release-surface inventory independently enumerates the six outside-subtree scripts/tests/e2e files directly bound into the historical Alpha release workflows. These inventories are provenance metadata only: they do not migrate historical code, authorize experiments, unlock outcomes, or change any scientific claim.

A historical source permalink is mechanically reconstructable as:

`https://github.com/vertex-studyAI/vertexED.ai/blob/9efb041d3d56e0dc617f5808576beff696d08a69/<source_path>`

Directory rows use the same commit-pinned `/tree/` form.

## What the map covers

The manifest set explicitly enumerates the material historical surfaces requested by issue #44: the embedded runtime/product and web implementation, Playwright/browser certification, packaging and OpenSCAD scripts, browser/OpenSCAD/CDN workflows, product-QA tests and generated Alpha product-QA outputs, public-alpha validation/docs, research status/claim/protocol/result/audit/manuscript surfaces, the historical benchmark/evaluator/direct-baseline and OOD package, the frozen component-ablation evaluator/workflow/test, successor-S3 protocol/adapter/authorization surfaces, Project 2424 evidence/state/project aliases, and both project-level and outreach-level external-pilot evidence templates.

The source inventory independently freezes the complete file-level contents of the embedded `T2424-0037` subtree, including top-level project/research/release documents, all historical `benchmark/` files, all embedded `src/` runtime files, and all `web/` files. The workflow inventory separately freezes the exact five explicitly NeuroCAD-named workflows at the repository root tree, while the release-surface inventory freezes the six directly workflow-bound outside-subtree scripts/tests/e2e files. Together, these controls prevent a future provenance edit from silently treating an omitted bounded historical surface as though it never existed.

Each surface row records:

- the historical path and immutable source commit;
- a blob/tree SHA where it was directly recovered during the handoff;
- either a canonical destination or the explicit `HISTORICAL_ONLY` status;
- an allowed relation (`IDENTICAL`, `MIGRATED_NON_SCIENTIFIC`, or `INTENTIONALLY_NOT_MIGRATED`);
- a current canonical cross-link for the reviewer;
- a note that states the evidence boundary.

The accompanying `tests/test_vertexed_historical_provenance.py` fails if required provenance categories disappear, source identities stop being immutable 40-character SHAs, base/extension historical paths collide, relative canonical cross-links do not exist, recovered blobs do not point to an existing base row, recovered generated-QA artifacts lose their non-scientific/historical boundary, the reviewer guide stops naming a provenance manifest in the machine-readable source-of-truth set, or frozen diagnostic/S3 execution surfaces are relabelled as migrated/authorizing results.

`tests/test_vertexed_source_inventory.py` separately binds the 48-file inventory to the exact source snapshot, exact source tree, exact entry count, and a canonical SHA-256 over every relative path/blob-SHA pair. It also fails if any manifest row inside the frozen `T2424-0037` subtree names a path absent from the inventory, or if a recovered/exact blob identity disagrees with the frozen inventory.

`tests/test_vertexed_workflow_inventory.py` binds the explicitly NeuroCAD-named workflow bucket to the frozen source snapshot/root tree, exact five-workflow set, exact Git blob identities, and manifest ownership while preserving the OOD/non-authorizing evidence boundary.

`tests/test_vertexed_release_surface_inventory.py` binds the six directly workflow-referenced outside-subtree release surfaces to the same frozen snapshot/root tree and their exact Git blob identities. This bounded inventory is release provenance, not evidence that any historical scientific result improved.

## Why historical surfaces remain `HISTORICAL_ONLY`

The old NeuroCAD Alpha lived inside VertexED and used a Node/browser packaging path. The canonical NeuroCAD repository now has an independently maintained Python runtime, release workflow, tests, and research-control plane. Treating those newer surfaces as byte-identical migrations would manufacture provenance. Instead, historical product/browser/release evidence stays pinned at its original VertexED commit, while the manifests point reviewers to the current canonical owner that supersedes the function.

This is especially important for release evidence: the historical jsDelivr workflow certified immutable artifact transport but explicitly did **not** establish an executable public browser host. Current release claims must therefore come from [`PUBLIC_ALPHA_EVIDENCE_LEDGER.md`](PUBLIC_ALPHA_EVIDENCE_LEDGER.md), not from the old VertexED workflow.

The same rule applies to product QA. The recovered `artifacts/neurocad-alpha/NEUROCAD_ALPHA_PRODUCT_QA.md` and `artifacts/neurocad-alpha/product-qa.json` artifacts are evidence of their original Alpha product-QA run only. Their source boundary explicitly distinguishes product QA from a scientific/OOD benchmark, so the provenance handoff retains them without promoting them into successor, held-out, or scientific evidence.

The same rule applies to research infrastructure. Historical `benchmark/evaluate.mjs`, the OOD package, and the component-ablation evaluator/workflow remain evidence for their original frozen packages. Historical S3 protocol/registry/authorization-generation files demonstrate that an authorization control plane existed; their presence does **not** authorize a canonical S3 run or permit outcome access.

## Scientific integrity boundary

Migration completeness is not scientific validation. The historical matched-validation diagnostic remains `VALIDATION_DOMINANT`; the typed-parser-specific causal interpretation remains **falsified**. Frozen v1/v2 evidence is not rewritten, promoted, or rerun by this provenance work. Historical OOD files are not relabelled as fresh successor evidence. The recovered Alpha product-QA outputs are not relabelled as scientific/OOD evidence. Stage-2 and S3 outcome-access/authorization boundaries are unchanged. Current scientific interpretation remains controlled by [`RESEARCH_TRUTH.md`](../RESEARCH_TRUTH.md).

No missing pilot, benchmark, deployment, authorization receipt, or scientific evidence was recreated during this handoff. Historical outreach replies or invitations are not converted into completed external pilots.

## Reviewer procedure

1. Open all three JSON manifests in the original core manifest set—the core manifest, research extension, and product-QA extension—then also open the OOD extension and the three bounded completeness inventories: the 48-blob subtree inventory, five-workflow inventory, and six-file release-surface inventory.
2. Confirm all artifacts are pinned to snapshot `9efb041d3d56e0dc617f5808576beff696d08a69`; confirm the subtree inventory is additionally pinned to `portfolio/project2424/projects/T2424-0037` / tree `f741417e9710c3044044465bfeabc7a3cf185ca0`, and the workflow/release-surface inventories to root tree `c5aeb156a9c09f0408dfa3dd20bd770076b5ee76`.
3. Resolve a selected `source_path` at the pinned VertexED source snapshot; verify `source_blob`/`source_tree` when present, or consult `recovered_blob_identities` for base rows whose exact blobs were recovered later.
4. Check `canonical_destination`. If it is `HISTORICAL_ONLY`, keep the original artifact as the evidence owner rather than copying it into NeuroCAD.
5. Follow `current_cross_link` to the current canonical software/research owner.
6. For recovered Alpha product-QA rows, preserve `PRODUCT_QA_NOT_SCIENTIFIC_BENCHMARK`; do not reinterpret the QA outputs as successor, held-out, OOD, or scientific evidence.
7. For benchmark, OOD, component-diagnostic, and S3 rows, preserve their original authorization/outcome status. Do not infer permission to rerun or inspect results from source presence.
8. Do not use repository migration, CI health, packaging success, a complete bounded source inventory, or a demo as evidence that a historical scientific claim improved.

If a later reviewer discovers another material historical NeuroCAD surface outside the currently bounded inventories, add it as a new commit-pinned row to the appropriate manifest extension and, where applicable, extend the relevant bounded inventory with an explicit reviewable scope change. Do not modify the identity or interpretation of an existing frozen row. If any frozen inventory disagrees with its pinned source tree, treat that as a provenance-control failure rather than silently editing the historical identity.
