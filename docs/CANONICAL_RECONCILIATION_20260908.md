# Canonical-history reconciliation candidate

## Checklist

- [x] Preserve the existing GitHub main and audited candidate branches.
- [x] Inspect the independent roots; neither clone is shallow.
- [x] Port main's PR #48 structural verification capability, retaining strict
  dimension/IR validation, collision refusal, and bounded claim language.
- [x] Add deterministic report/hash, invalid-input, and output-collision tests.
- [x] Join histories on this integration branch and verify both parents remain ancestors.
- [x] Run the maintained suite: 387 passed in 146.33 seconds; Ruff and mypy pass.
- [x] Build wheel/sdist; distribution safety checks pass (46/194 archive members).
- [x] Open draft NeuroCAD PR #49 with the explicit baseline-adoption decision.
- [ ] Remote CI on the final PR revision must pass; local results are not substituted.
- [ ] Review the full audited-baseline adoption diff before merging into main.

## Portal follow-up

- [x] Detect that PR #70 was merged externally and preserve its updated main.
- [x] Open scoped PR #71 for the remaining Vercel provenance issue.
- [x] Treat generated `.vercel/` as build metadata; do not ignore tracked config changes.
- [x] Require exact Vercel commit/HEAD identity and restore config formatting only
  when parsed JSON is identical. Changed values still fail, followed by the
  unchanged strict Git cleanliness check. Regression tests and PR #71 CI pass.
- [ ] Verify hosted preview: **blocked by Vercel account build-rate limit**.
  Retry once quota is available; no plan purchase or limit bypass was attempted.
  Configuration-value rewrites, if present, will still block and require inspection.

PRs: https://github.com/THE-BU1LD/NeuroCAD/pull/49 and
https://github.com/build-the-future-11/finance4all-global-reach/pull/71.
Neither was merged by this execution.

## Explicit tree decision

The integration adopts the existing audited 0.5.0a6 tree as the maintained product,
not a file-by-file union with the older public-alpha tree. The audited baseline
already moved generated/legacy surfaces out of supported packaging and changed
prompt acceptance to explicit dimensions. Restoring the old permissive generator
or old release workflows would undo those boundaries.

Canonical main at `b7db704` remains intact in Git history. Its only change since
`284923c` is PR #48 (README, CLI verification, two tests); that capability is now
ported into `core/structural_verification.py` and exposed through `neurocad verify`.
The old tests used incomplete dimensions; the adopted tests instead verify strict
dimensioned input and explicitly assert rejection of the old incomplete example.
No learned experiment or physical result is manufactured by this integration.

The history-joining merge deliberately retains the audited tree after that port.
It does NOT claim the two trees were identical or resolve every historical
behavior change automatically. Both parent histories remain recoverable; no
force-push, root replacement on main, or duplicate 235 MB source archive is needed.

This is a **review candidate**, not authorization to merge. Reviewers must inspect
the broad baseline adoption, legacy relocation, historical research differences,
and packaging boundaries. Old main can always be inspected at its immutable SHA.
Remote CI verifies the maintained product, not equivalence of every legacy path.
