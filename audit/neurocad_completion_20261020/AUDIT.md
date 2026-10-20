# NeuroCAD bounded completion successor audit - 20 October 2026

This audit applies the requested start-to-finish pipeline to the current merged
NeuroCAD line without overwriting the dated 44-item audit in
`audit/comprehensive_20261017/FLAW_CHECKLIST.md`. It is a current successor, not
a claim that all possible defects are known.

## Outcome

The locally executable product successor is implemented and focused-verification
passes. The research program is not globally complete: independent challenge
data, physical measurements, independent reproduction, intended-user evidence,
hosted exact-head verification, and a new immutable release remain external or
infrastructure-blocked.

## Concrete flaw -> cause/evidence -> severity -> repair -> acceptance evidence

| Flaw | Cause / evidence | Severity | Repair | Acceptance evidence |
|---|---|---:|---|---|
| Malformed Feature IR scalars could leak raw Python type/hash failures | Lists or objects reached set/dict membership in the public validation path | High | Validate every identifier, kind, unit, role, selector and output scalar before hash/set use | Current `tests/test_feature_ir.py` batch passes with the integrated successor |
| Accepted enclosure revisions could silently move selected connector or mounting interfaces | Revision history preserved fields but had no external lock contract | High | Added exact-source contracts for named cutouts, standoffs, PCB mounting and modeled lid/body fields; protected commands reject before write | `tests/test_interface_contract.py`: 6 passed, including CLI refusal and report recomputation |
| A nominal connector lock could miss a manufacturing-profile change to the compiled opening | Circular-hole compensation depends on the selected profile, while the recovered lock initially captured only nominal fields | High | Added manufacturing-profile plus compiled aperture/hole snapshots for locked cutouts and standoffs | A connector-only lock now rejects a profile change; final interface/fit-revision regression passed 11 tests with Ruff and MyPy |
| Revision review did not state which prior evidence became stale | A semantic diff named values but not evidence dependencies or ancestry violations | High | Added stable-ID, coordinate-level change-impact reports with exact source/candidate hashes, ancestry checks and invalidation classes | Saved report tampering and unrelated ancestry are rejected in focused tests |
| Fit coupons relied on filenames to distinguish variants | Coupon geometry had no physical variant code | Medium | Added an anchor plus five-bit through-hole marker and bounded aperture adjustment | Fit-study tests regenerate IR/SCAD and compare declared aperture geometry |
| A generated worksheet could be mistaken for measured evidence | Templates did not force complete process identity and all trials | Critical claim risk | Added strict printer/process passport, predeclared replicated trials, conservative all-replicate decisions and descriptive Wilson intervals | Incomplete, duplicate, stale and non-monotone inputs fail or remain explicitly unresolved |
| Attached photos or calibration files could drift after review | No immutable inventory bound external files to the report | High | Added atomic evidence bundles with sizes, SHA-256 hashes, normalized observations and a recomputable report | Byte tampering and report mutation are rejected; authenticity remains explicitly unclaimed |
| A fit result could be applied twice or to a stale project | No single-use exact-source revision plan | High | Added review-only fit-revision plans, explicit `--confirm`, exact project/study/report/evidence bindings, isolated cutout edits and independent applied-revision verification | Stale, unbracketed, tampered and double-application paths are rejected |
| Full/native local verification could exhaust this host | Latest free plus speculative memory was about 331 MiB and pageouts rose during the session | Critical resource gate | Enforced the repository's 512 MiB/no-rising-pageout stop rule | Heavy/full/native/package runs were not executed and are not reported as passes |
| Hosted verification cannot currently execute | Existing PR workflows received zero runner steps because of the GitHub billing/spending-limit condition | High release gate | Preserve the failure; rerun only after account admission is repaired | No hosted pass is claimed for this successor |
| Remote transmission is not yet authorized at exact payload/destination scope | Push of local commit `3030ea5` to private remote `build-the-future-11/NeuroCAD`, branch `codex/neurocad-perfect-20261020`, was rejected by managed external-transmission review | High delivery gate | Obtain explicit user approval naming this commit, remote and branch; do not route around the gate | Local commit is preserved and the remote branch remains at `8133960` |
| A new Kaggle result was requested without a frozen Kaggle study or independent data | NeuroCAD's active confirmatory compiler protocol requires independently authored/adjudicated prompts; no Kaggle dataset/bundle is authorized | Critical research gate | No upload or fabricated result; materialize and hash the independent challenge first, then freeze a successor execution package | Kaggle uploads and protected runs remain zero |
| The requested `arxiv.sty` is absent | No such file exists in the repository or indexed user files | Medium packaging gate | Preserve the complete existing Physics v2 manuscript and compiled PDF; require the exact style asset before a style-specific successor package | Desktop LaTeX compilation succeeded; all six committed PDF pages were visually inspected with no clipping or overlap |

## Verification executed on the current checkout

- 23 fit-study and fit-sample tests passed.
- 5 fit-revision tests passed.
- 26 interface-contract plus Feature IR tests passed.
- Scoped Ruff passed.
- MyPy passed for five changed source files.
- `git diff --check` passed.
- The existing six-page Physics v2 LaTeX source compiled successfully in the desktop compiler; its committed PDF was visually inspected page by page.
- After the final compiled-aperture lock correction, 11 interface and fit-revision tests passed; scoped Ruff and MyPy passed again.

One combined test command reached its 30-second command ceiling after printing
progress but before a terminal summary. It is not counted as a pass. The same
tests were split into three bounded batches and all completed successfully. An
initial command used absent `.audit-venv/bin/python` and failed before test
collection; the repository's existing `.venv` was then used.

## Honest completion boundary

The implementation now supports a complete local path from source-bound fit
variants through observation accounting, evidence sealing, review-only revision,
protected-interface enforcement and recomputable impact reporting. No coupon was
printed or measured here. No new paper result, model efficacy result, Kaggle
result, physical-fit claim, manufacturing certification, independent replication,
user-study outcome, hosted exact-head pass, release, or arXiv submission was
created.

The final local payload is commit `3030ea5` (20 files, 4,477 insertions and 24
deletions). A push to `build-the-future-11/NeuroCAD` branch
`codex/neurocad-perfect-20261020` was attempted and rejected by the managed
external-transmission gate pending explicit destination/payload approval. No
alternative transmission path was attempted.

## Next action

Repair GitHub Actions admission and run the exact-head full/native/package matrix.
Separately, obtain the independently authored/adjudicated challenge and strong
comparator identities before freezing any new compiler study. Physical fit needs
real coupons, calibrated metrology, retained failures, and held-out confirmation.
