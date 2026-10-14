# Verified NeuroCAD work closure — 14 October 2026

The current repair set is merged in [PR109](https://github.com/THE-BU1LD/NeuroCAD/pull/109) at `079902fa20d22c2cf102104b0f42b28bec8bc382`. Its tree is identical to tested candidate `d7a80567c2c2727f8bd420a68e2517b217508b56`. [Main CI](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38565917174) passed all ten required jobs. This is bounded software evidence.

- 1,677 maintained tests passed; 9 skipped and 53 subtests passed on each required Python version.
- The extracted source distribution passed 1,658 tests, with 9 skips and 33 subtests.
- All required Linux/macOS/Windows and Chromium/Firefox/WebKit checks passed.
- 37/37 scalar cases, 52/52 isolated-wheel cases/workflows and four compiled composite meshes passed.
- 42 new composite references passed: 14 shaft cases, 18 rational polygon section/structural cases, two perforated-plate integral cases and eight actual hole-boundary distance cases.
- Optional exact CAD passed 106 tests; native exact CAD/Gmsh passed 174 tests and 17 constructed revision cases.
- Full dependency/security gates passed. All 52 reviewed low-severity findings remain tied to exact source hashes; new findings or drift fail. No file or rule was excluded.

The opposing-load beam correction is included. The later shaft baseline retained four failures in six cases, including a false yield pass: 9.6766 MPa reported versus 11.0347 MPa reference at a 10.5 MPa limit. The correction maximizes stress over the entire circular boundary. A second correction changes single-hole edge ligaments from the unrelated configured margin to actual geometry (45/35 mm in the retained example, previously 15/15 mm). Earlier cases, thresholds, source identities and failures remain intact.

All 17 originally open repair PR histories are incorporated; no open PR remains. Issues 2, 5, 11, 44, 58, 60 and 68 are closed. The historical inventory now covers 157 pinned source entries. Main protection enforces ten checks, mandatory PRs, resolved conversations and admin enforcement, without force pushes or deletion. Approving-review count is zero because the repository has only one write-capable collaborator; independent approval is not claimed.

| Original validation gate | Truth now |
|---|---|
| Freeze contracts | Versioned source-bound contracts retained; all 40 protected v2/release/paper files match. |
| Verify calculations | Declared scalar and composite reference cases pass, including scale/sign/zero-load and rejection checks. This is a sampled analytical envelope. |
| CAD-to-analysis workflows | Declared installed, browser, edit/invalidation, mesh and native fixtures pass. Full future native shape/platform matrices remain open. |
| Physical accuracy | Not executed; calibrated measurements and uncertainty records are required. |
| Independent reproduction | Not executed; an external executor must produce and inspect results. |
| Intended-user usability | Not executed; intended users must perform and interpret the tasks. |

Thirteen tracked issues remain, including the native shape/platform acceptance in 64/65 and external research/data/user dependencies. All 109 expansion proposals remain separately scoped. The published immutable alpha is still v0.5.0a6; these repairs are on main and have not been tagged as a new release. The original dirty checkout was preserved; verified implementation lives in `/Volumes/PRO-BLADE/.codex-worktrees/neurocad-physics-v3-fix` and remote main.

Raw logs, exact run metadata, source identities and final issue/PR routing are retained alongside this report. Empty external-study templates are not completion evidence.
