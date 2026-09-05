# Historical VertexED → NeuroCAD provenance

This document closes the repository handoff tracked by NeuroCAD issue #44 without copying or rewriting historical evidence. The machine-readable source of truth is [`vertexed_neurocad_provenance_v1.json`](vertexed_neurocad_provenance_v1.json).

## Pinned historical source

- Repository: `vertex-studyAI/vertexED.ai`
- Snapshot: `9efb041d3d56e0dc617f5808576beff696d08a69`
- Historical migration tracker: `vertex-studyAI/vertexED.ai#491`
- Canonical owner: `THE-BU1LD/NeuroCAD`

Every manifest row is pinned to that source snapshot. Where a blob SHA was directly recovered, it is recorded as `source_blob`; otherwise the immutable commit plus path remains the provenance identity. A historical source permalink is therefore mechanically reconstructable as:

`https://github.com/vertex-studyAI/vertexED.ai/blob/9efb041d3d56e0dc617f5808576beff696d08a69/<source_path>`

Directory rows use the same commit-pinned `/tree/` form.

## What the map covers

The manifest explicitly enumerates the material historical surfaces requested by issue #44: the embedded runtime/product implementation, Playwright/browser certification, packaging and OpenSCAD scripts, browser/OpenSCAD/CDN workflows, product-QA tests, public-alpha validation/docs, research status/claim/protocol/result/audit/manuscript surfaces, the Project 2424 evidence alias, and both project-level and outreach-level external-pilot evidence templates.

Each row records:

- the historical path and immutable source commit;
- a blob SHA where it was directly recovered during the handoff;
- either a canonical destination or the explicit `HISTORICAL_ONLY` status;
- an allowed relation (`IDENTICAL`, `MIGRATED_NON_SCIENTIFIC`, or `INTENTIONALLY_NOT_MIGRATED`);
- a current canonical cross-link for the reviewer;
- a note that states the evidence boundary.

The accompanying `tests/test_vertexed_historical_provenance.py` fails if required provenance categories disappear, source identities stop being immutable 40-character SHAs, duplicate historical paths are introduced, relative canonical cross-links do not exist, or the frozen diagnostic/audit surfaces are relabelled as migrated results.

## Why most historical surfaces remain `HISTORICAL_ONLY`

The old NeuroCAD Alpha lived inside VertexED and used a Node/browser packaging path. The canonical NeuroCAD repository now has an independently maintained Python runtime, release workflow, tests, and research-control plane. Treating those newer surfaces as byte-identical migrations would manufacture provenance. Instead, historical product/browser/release evidence stays pinned at its original VertexED commit, while the manifest points reviewers to the current canonical owner that supersedes the function.

This is especially important for release evidence: the historical jsDelivr workflow certified immutable artifact transport but explicitly did **not** establish an executable public browser host. Current release claims must therefore come from [`PUBLIC_ALPHA_EVIDENCE_LEDGER.md`](PUBLIC_ALPHA_EVIDENCE_LEDGER.md), not from the old VertexED workflow.

## Scientific integrity boundary

Migration completeness is not scientific validation. The historical matched-validation diagnostic remains `VALIDATION_DOMINANT`; the typed-parser-specific causal interpretation remains **falsified**. Frozen v1/v2 evidence is not rewritten, promoted, or rerun by this provenance work. Stage-2 and S3 outcome-access/authorization boundaries are unchanged. Current scientific interpretation remains controlled by [`RESEARCH_STATUS.md`](RESEARCH_STATUS.md).

No missing pilot, benchmark, deployment, or scientific evidence was recreated during this handoff. Historical outreach replies or invitations are not converted into completed external pilots.

## Reviewer procedure

1. Open the JSON manifest and select a `source_path`.
2. Resolve it at the pinned VertexED source snapshot above (and verify `source_blob` when present).
3. Check `canonical_destination`. If it is `HISTORICAL_ONLY`, keep the original artifact as the evidence owner rather than copying it into NeuroCAD.
4. Follow `current_cross_link` to the current canonical software/research owner.
5. Do not use repository migration, CI health, packaging success, or a demo as evidence that a historical scientific claim improved.

If a later reviewer discovers another material historical NeuroCAD surface, add it as a new commit-pinned manifest row rather than modifying the identity or interpretation of an existing frozen row.
