# NeuroCAD current status

Reconciled 2026-10-13 against clean starting commit
`a7eb80c54e3133e018b37e595413622dc0687a4a`. Product changes are committed on `codex/enclosure-verification`.

| Line | Status | Authoritative evidence | Remaining boundary |
| --- | --- | --- | --- |
| Original compiler study | Terminal mixed | `TERMINAL_STATUS_2026-10-11.md`, `NC-REPRO-508EC40` | Synthetic bounded grammar; historical typed-parser claim remains falsified |
| Physics v2 | Supported within controlled contract; locally packaged | [v2 state](research/physics_v2/RESEARCH_STATE.md), local `physics-v2-v1.0.0` tag | 216 synthetic conformance cases; no independent reproduction, physical validation, or submission |
| Physics v3 | Engineering implemented; scientific validation not started | [v3 state](research/physics_v3/RESEARCH_STATE.md) | Retained 1,225-pass/9-skip receipt is historical, not a check of current edits |
| Enclosure product | Hosted fresh-install and compiled-enclosure acceptance passed | [acceptance procedure](docs/ENCLOSURE_ACCEPTANCE.md) | Internal Linux/Python 3.12 engineering verification; physical and independent validation remain open |
| Public alpha | Release candidate; publication not verified | `RELEASE_STATUS.md` historical release gates | No local `v0.5.0a6` tag; remote release state not checked this session |

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
- Immutable public product release provenance and
  credential-free tagged-release installation.

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
