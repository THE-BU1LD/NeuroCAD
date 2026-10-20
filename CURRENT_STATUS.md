# NeuroCAD current status

## Feature IR fail-closed hardening candidate — 2026-10-20

The merged upstream engineering baseline is
`ca15203738fd45113ace7ee649543a42717c5787` (PR115). Candidate code
`14c2e10edd288d8ebf8be6afe5e295f2f4307a90` makes malformed Feature IR
scalar fields fail closed with `FeatureIRParseError` rather than leaking raw
Python hash/type failures. The maintained Feature/Requirement IR gate passed
71 tests with 7 native-dependent skips, and its scoped Ruff gate passed.

This is a bounded engineering candidate, not a new release or scientific
result. The heavy/native local suite was not admitted: free plus speculative
memory was 240.9375 MiB, below the repository's 512 MiB floor. Hosted
verification was attempted, but GitHub allocated no runner and executed zero
steps because the account requires a billing or Actions spending-limit repair.
PR1 remains unmerged. Published `v0.5.0a6`, frozen research artifacts, negative
results, and external physical, independent-reproduction, safety, and
intended-user gates are unchanged. See the
[candidate receipt](docs/verification/feature-ir-hardening-20261020/REPORT.md).

## Native acceptance and provenance follow-up — 2026-10-14

All three native platforms passed five exact-CAD goldens, six repeated tagged
mesh runs and 182 rejection/native tests on candidate `bf4cdca`. The full product
matrix and interoperability passed. PR110 carries the implementation and the
preservation follow-up; final merge/check identity is tracked in the
[native acceptance receipt](docs/verification/native-acceptance-20261014/REPORT.md).

A fresh [historical provenance audit](docs/RESEARCH_PROVENANCE_AUDIT_20261014.md)
found one missing run log and timing fields in the original v1 digest. Original
artifacts remain untouched; new timing extraction uses format v2. The frozen
paper stays unchanged and the erratum is separate. External physical, independent
and intended-user gates remain open; the published alpha tag is unchanged.

## Current engineering closure — 2026-10-14T12:50:09.899036+00:00

PR109 merged the integrated repairs at `079902fa20d22c2cf102104b0f42b28bec8bc382`. Exact-main CI passed 1,677 maintained tests; source-distribution, OS/browser, security and native gates passed. The declared conformance envelope passes 37 scalar, 52 installed and 42 new composite reference cases. [Complete receipt](docs/verification/composite-final-20261014/REPORT.md).

Physical validation, independent reproduction and intended-user studies remain unexecuted. Native shape/platform acceptance in issues64/65 and other tracked external dependencies remain. Published v0.5.0a6 is unchanged. The original dirty checkout is preserved; source location: `/Volumes/PRO-BLADE/.codex-worktrees/neurocad-physics-v3-fix`. Prior dated records follow unchanged.

## Public alpha complete — 2026-10-14

**`v0.5.0a6` is published and verified** at commit
`5ce2092db7203cf2bd532a742ea0697e1cf8479c`.
[Release](https://github.com/THE-BU1LD/NeuroCAD/releases/tag/v0.5.0a6) · [passing release/anonymous-install workflow](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38498546483).
Full main CI `38495962707` passed all ten matrix jobs; the preceding PR also
passed enclosure and CAD/Gmsh integration checks. Bugbot completed with no issues.
Published wheel and sdist hashes were independently rechecked against provenance.
Both credential-free wheel installation through the public installer and the
default tagged-source installer passed; edited body/lid mesh acceptance passed.
Persistent OS service setup, physical fit and independent science are outside
this receipt. [Completion report](docs/verification/alpha-20261014/REPORT.md).

All dated candidate/pending entries below are retained history, superseded for
public-release status by this receipt. Scientific conclusions remain unchanged.

Reconciled 2026-10-13 against clean starting commit
`a7eb80c54e3133e018b37e595413622dc0687a4a`. Product changes are committed on `codex/enclosure-verification`.

| Line | Status | Authoritative evidence | Remaining boundary |
| --- | --- | --- | --- |
| Original compiler study | Terminal mixed | `TERMINAL_STATUS_2026-10-11.md`, `NC-REPRO-508EC40` | Synthetic bounded grammar; historical typed-parser claim remains falsified |
| Physics v2 | Supported within controlled contract; locally packaged | [v2 state](research/physics_v2/RESEARCH_STATE.md), local `physics-v2-v1.0.0` tag | 216 synthetic conformance cases; no independent reproduction, physical validation, or submission |
| Physics v3 | Engineering implemented; scientific validation not started | [v3 state](research/physics_v3/RESEARCH_STATE.md) | Retained 1,225-pass/9-skip receipt is historical, not a check of current edits |
| Enclosure product | Hosted fresh-install and compiled-enclosure acceptance passed | [acceptance procedure](docs/ENCLOSURE_ACCEPTANCE.md) | Internal Linux/Python 3.12 engineering verification; physical and independent validation remain open |
| Public alpha | Published prerelease; anonymous installation PASS | `docs/verification/alpha-20261014/REPORT.md` | Bounded alpha; physical and independent validation remain open |

## Engineering changes

Project publication now refuses replacement atomically. Bundle verification can
require the exact expected project revision and compiled meshes. Installed-wheel
CI acceptance now exercises interpretation, edits, unchanged fields, rejection,
mesh verification, stale revisions, collisions, and tampering outside the source
import path. The implementation at `5351903` passed hosted verification, including a fresh
wheel install and compiled body/lid acceptance.

## Evidence preserved

No files under `research/`, `paper/`, or `release/physics_v2/` were changed by this
product task. No frozen case, protocol, execution ledger, tag, or scientific result
was rerun or reinterpreted. Old truth/status narratives remain explicitly scoped
historical records; the version index takes precedence for current routing.

## Still needs external evidence

- Physics v2 independent execution using its external reproduction procedure.
- Independently authored/adjudicated compiler challenge and strong comparator.
- Separately frozen Physics v3 validation; no scientific study has started.
- Physical enclosure fit/calibration and human usability measurements.
- Public product release provenance and credential-free tagged-release installation
  completed on 2026-10-14; see the completion receipt above.

## Earlier local checks (historical)

- 11 focused tests passed (atomic publication, enclosure CLI workflow, installer
  failure injection, and edit grammar).
- Scoped Ruff and MyPy (5 source files) passed. Bandit was unavailable in the local environment.
- [Source acceptance receipt](docs/verification/enclosure-20261013/SOURCE_ACCEPTANCE.json)
  passed against the existing development environment without compiling meshes.
- Fresh dependency installation, wheel build, full test suite, compiled-mesh
  acceptance and hosted CI were not executed. Resource samples remained below
  512 MiB and pageouts rose. Process/swap inspection was sandbox-denied.

These results do not certify a clean installation or independent validation.

## Earlier resource recheck (historical)

Fresh samples measured 163.5 and 114.625 MiB, with pageouts increasing from
135420 to 136334. Fresh installation, compiled acceptance, and commit remain
pending. The hosted CI lookup succeeded on retry: runs 38026811475 and
38026811472 passed on `f560df8dfd31d0df9bf5886ec78a1fab839e3f5a`, which does not
verify the local candidate. An hourly follow-up now rechecks admission and will
resume the authorized verification when it passes, retaining failures and frozen
research. See `docs/verification/enclosure-20261013/RESOURCE_RECHECK.json`.

## Remote verification history

The candidate is committed on `codex/enclosure-verification`. GitHub run
38424324609 on 951f8b8 executed 1,226 passing tests with 9 skips and one failure:
the new publication regression test omitted an explicit UTF-8 encoding. The
omission is corrected; a replacement run will verify the fix and the remaining
wheel/mesh gates. Local resource blockage no longer blocks remote execution.

## Verified hosted result

[Run 38425980085](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38425980085)
passed on `53519038250e8aa3f6b76aeead63cc4a23be2ada`: 1,227 tests passed,
9 skipped; Ruff, MyPy, Bandit and dependency consistency passed. The built wheel
installed into a new virtual environment and passed compiled body/lid enclosure
acceptance outside the checkout, including exact-revision checks, invalid edits,
collision protection and tampering rejection. [Retained receipt](docs/verification/enclosure-20261013/ci-38425980085/SUMMARY.json).

The first three hosted failures and their fixes are retained in the receipt.
Local memory remains blocked; this successful execution used GitHub resources.
No frozen research, original scientific outcome, or research tag changed.
Independent reproduction, physical fit, human usefulness and public tagged
product release remain unverified. A final documentation commit is separately
checked by the same hosted workflow before completion is reported.

## Public alpha execution — 2026-10-14

Final documentation commit `6151d93` passed enclosure run `38426643691`.
Full release matrix `38494422164` passed all three browsers and exact CAD, but
failed a test lint rule and Windows collection of the POSIX-only frozen research
harness. Repairs preserve portable product physics coverage and frozen research.
The repository-only study harness is excluded from the source distribution, as
it requires unshipped study artifacts and Git provenance; product tests remain.
A post-publication workflow now verifies public checksums, exact source provenance,
prerelease status, the tagged installer, and installed compiled-enclosure behavior
without download credentials. Release remains pending until all gates pass.

## Physics v3 frozen conformance — 2026-10-14

The new frozen matrix passed 31/32 cases locally and in CI; an opposing-load
beam case exposes underestimated maximum bending stress (0 versus 2.1 MPa).
Installed workflow acceptance passed 15/15, four shapes compiled, and regression
passed 1,230 tests with 9 skips. The overall gate remains FAIL. Protected v2,
release and paper files are unchanged; physical, independent and user validation
remain open. See [the retained report](docs/verification/physics-v3-20261014/REPORT.md).

## Corrected Physics v3 conformance successor

The separately frozen validation_v2 successor corrects opposing-load maximum
beam stress by considering interior moment extrema. All 37 source scalar cases
pass. Prior v1 outcomes are known and retained: this is regression conformance,
not blinded confirmation. Hosted run 38557278466 passed on 5676436: 52/52 installed cases/workflows,
four mesh compilations and 1,236 regression tests passed (9 skipped). External
validation tooling passed 11 integrity tests; no physical, independent or human
evidence has been collected. See docs/verification/physics-v3-corrected-20261014/REPORT.md.
