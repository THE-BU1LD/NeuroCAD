# Integrated work audit and verification

The candidate `e71b63c829f02ed2950dea12912dd4149056904a` passed the complete hosted software matrix. It incorporates the compatible histories of 17 open repair PRs and preserves earlier failed studies. PR: https://github.com/THE-BU1LD/NeuroCAD/pull/107.

| Check | Result | Receipt |
|---|---|---|
| Python 3.10/3.11/3.12 | 1,632 passed, 9 skipped, 48 subtests on each | [CI](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38562266257) |
| Actual source distribution | 1,616 passed, 9 skipped, 33 subtests | Same CI; repository-only frozen study fixtures remain separately tested |
| Portable operating systems | Linux, macOS, Windows passed; platform exclusions retained | Same CI |
| Real browsers | Chromium, Firefox, WebKit passed | Same CI |
| Physics source / isolated wheel | 37/37 scalar; 52/52 installed; four compiled meshes | [Conformance](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38562257572) |
| Optional exact CAD | 106 passed | Same matrix CI |
| Native exact CAD to Gmsh | 174 passed; 17/17 constructed revision cases and mesh passed | [Native CI](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38562266781) |
| Security | Dependency audit passed; full Bandit scan with 39 exact source-bound low-finding reviews | Full failed and successful scans retained; no rule or file skipped |
| External evidence integrity | Passed; collection templates remain empty | [Integrity CI](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38562266234) |

Two unsuccessful integration attempts are retained. The first required explicit review of fixed-vector subprocess use and deterministic numerical-reference RNG in frozen harnesses. The second exposed workflow-text contract defects introduced during that repair. Workflow formatting and argument order were corrected; the gate tests were not weakened. Fifteen focused gate tests passed locally before the third hosted attempt.

The existing immutable alpha release was rechecked live. Issues 2, 5, 11 and 60 were closed against that release's receipts. Issue 58 was closed after enabling and reading back strict main-branch protection: ten stable checks, mandatory pull requests, resolved conversations, admin enforcement, and no force-push/deletion. Required approving reviews remain zero because the repository has only one write-capable collaborator; this is not independent code approval. Issue 68 was closed after checking the unchanged main implementation against the native requirement and adversarial revision tests.

The historical handoff now records 157 entries at the pinned VertexED commit, including 107 repository-wide text-reference paths. Every object identity was checked against the source tree; prior ownership and evidence classes remain unchanged. Seventeen existing provenance tests passed.

## Frozen protocol count clarification

The inherited narrative in validation_v2 and validation_v3 says 32 scalar cases. Their frozen case arrays actually contain 37: the original 32 plus five explicitly described successor beam cases. Executed receipts use 37. This annotation corrects the presentation without changing any frozen protocol, reference, tolerance or case. V1 remains the original 31/32 failure.

## Unfinished scope

This is software conformance. Physical measurements, independent execution and intended-user observations do not exist. Composite section properties and every structural output still need broader independent-reference coverage; current composite workflow acceptance is bounded to the frozen checks. The exact CAD/Gmsh fixtures do not close every future shape/platform goal. The 109 expansion proposals are explicitly outside current-alpha acceptance. The integrated candidate awaits review/merge and is not a new release.
