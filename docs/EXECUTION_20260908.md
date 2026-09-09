# Master TODO execution — 2026-09-08

This is an implementation record, not a declaration that the full backlog is
complete. Public release, production acceptance, and physical testing remain
separate gates. Earlier audit snapshots are historical, not current bug lists.

## Implemented in this execution

- CAD workbench: optional real OpenSCAD compilation, topology verification,
  enclosure feature verification, actual triangle-mesh isometric previews,
  body/lid selection, and downloads of the same verified STL bytes. The fast
  schematic remains explicitly unverified. Compilation is serialized, each part
  has a 30-second timeout, previews are capped at 20,000 faces, and each download
  at 8 MiB. Temporary source/mesh files are cleaned up.
- Browser downloads use a bounded 32 MiB memory cache, unpredictable URLs,
  attachment responses, and ten-minute expiry; older downloads can be evicted.
  Missing downloads require recompilation. These are local demo artifacts,
  not authenticated persistent project storage.
- OpenSCAD integration discovery reports `available`, not `verified`, when only
  executable detection has occurred. Actual verified artifact receipts retain
  their `verified` state. Consumers must accept the additional capability state.
- Portal: administrative deletion review requires the returned requested row;
  optional avatar synchronization changes local state only after confirmation.
- Portal search: exact-title, prefix-title, then remaining substring tiers are
  filtered before per-table limits. Ties use stable IDs, then category. Each tier
  queries six authorized tables and stops once twelve results are available;
  worst case is eighteen bounded requests. No RLS or database grants changed.
- News/opportunity/event search links carry selected record IDs. Their destination
  hooks fetch the selected record directly rather than searching a truncated
  list; users can return to the full list.
- Installed Percy/Lyla runtime: pause/disabled/autopilot gates at submission,
  claim and pre-execution; reseeding cannot raise existing execution authority;
  explicit task-detail lookup; Lyla vNext payload translation; idempotent
  submissions; rejection/uncertain delivery cannot fall back to another executor.
- Percy no longer verifies provider prose. Operator-owned task acceptance commands
  must pass; absent/invalid/failed checks leave `VERIFYING`. Commands have bounded
  wall time and process-group cleanup. This is not isolation against malicious
  code running as the same OS user. Existing historical receipts are preserved.
- Percy wrapper now targets the installed vNext implementation; foreground default
  port is 8787, avoiding Lyla's 8765. Broader repository/runtime consolidation is
  not yet complete.
- Running provider/acceptance processes are cancelled on shutdown or revoked
  project authority. Output is capped in memory and process groups are cleaned up.
- Provider discovery checks authentication/local model presence without spending
  on model calls. Unavailable requested providers cannot silently fall back.
  The LaunchAgent resolves the current local Codex CLI before the old Homebrew
  binary. Discovery explicitly does not claim verified model execution.

## Product boundary

Keep the established FinanceMeta portal separate for this release. It is not
silently rebranded or presented as CAD project storage. A shared CAD membership
workspace requires an explicit ownership/storage/retention contract before
cross-product data is connected. No CAD cloud-storage feature is claimed here.

## Validation

- Initial CAD baseline: 376 tests passed.
- Final full CAD suite: **382 passed in 117.47 seconds**, with localhost
  permissions for HTTP tests. An earlier sandboxed run returned
  375 passed, two failed and five setup errors, all seven due to denied socket
  binding; no tests were disabled or assertions removed.
- CI-scope Ruff passed; CI-scope mypy passed across 58 source files; Bandit on
  `core` passed.
- Wheel and sdist built with the pinned tools in `.tmp-release-work/venv`.
  Distribution safety verification passed: 191 sdist members, 45 wheel members.
  An earlier no-isolation build in the Python 3.11 test environment failed because
  its setuptools/wheel did not match the build pins; requirements were not weakened.
- The final wheel was installed with `--no-deps --no-index --target` into
  `/private/tmp/neurocad-wheel-check.ULdMik/site`. From outside the checkout, the
  preview module resolved to that installed path; the CLI accepted a supported
  plate and rejected an unsupported warp drive (expected exit 1). Dependencies
  came from the existing release environment: this is not a fresh online install.
- Portal `npm run typecheck`, `npm run lint`, `npm test`, and `npm run build:dev`
  passed after final changes. Development build is not a release provenance receipt.
  Final repeated test command: 91 Vitest tests in 24 files, 23 Node contract tests,
  and six release-toolchain tests passed.
  Vitest uses two isolated thread workers after fork-worker startup failures in
  this environment; test isolation and assertions remain enabled.
- Installed Percy safety tests: 15 passed. Lyla suite: 48 passed.
- Live localhost health: Percy 8787 and Lyla 8765 both returned `ok: true`.
  Percy reports Codex authenticated, Claude logged out, Gemini readiness unchecked,
  and configured Ollama model unavailable. No provider model execution is claimed.
- Browser: real enclosure compilation, body/lid selection, and mesh verification
  displayed successfully; narrow layout had no horizontal overflow. The original
  data-URL download did not yield a download event; its HTTP replacement produced
  a successful browser download event. HTTP tests also checked exact bytes,
  attachment/no-store headers, missing downloads, and hostile Host rejection.
- NeuroCAD Git-history secret scan: 78 commits, no leaks reported by Gitleaks.
  This is not proof that all possible secrets are absent.
- Portal Git-history scan: 62 commits, one finding. Inspection classified it as
  the literal documentation placeholder `Authorization: Bearer YOUR_ANON_JWT`
  in `DEPLOYMENT.md` at commit `5ec9d06a412754845e1a14dd4e2260efc0cb128c`.
  The raw scan therefore did not exit cleanly; no suppressions or history rewrite
  were added, and this placeholder is not an exposed credential.

## Still open

- Claude authentication (`claude auth login`), configured Ollama model availability,
  Gemini readiness integration, and real provider model execution remain unverified.
  Full canonical runtime packaging is unfinished local engineering work, not an
  external blocker or a completed release.
- Real PostgREST acceptance of the revised search tiers and selected-record flows.
- Production migration/authorization/lifecycle checks: no
  `FINANCEMETA_DATABASE_URL`, `E2E_MEMBER_A_EMAIL`, `E2E_MEMBER_A_PASSWORD`,
  `E2E_MEMBER_B_EMAIL`, or `E2E_MEMBER_B_PASSWORD` is present in this environment.
- Exact-revision external CI, canonical-history reconciliation, public artifacts,
  release provenance, and anonymous public installation.
- Physical coupons, measured fits, backup/restore rehearsal, and optional product
  extensions from the master TODO. These are not marked complete by documentation.
- Internal disk has critically low free space; do not delete unrelated user data
  or start large installs to bypass this limitation.

Frozen research protocols, negative evidence, and claim boundaries are unchanged.

## Files and runtime ownership

- NeuroCAD worktree: `core/mesh_preview.py`, `core/demo_server.py`, integration
  capability model/registry, regression tests, README, and execution/audit notes.
- Separate portal worktree `.portal-canonical`: search and selected-record hooks,
  three destination pages, account-review/avatar persistence, regression tests,
  and Vitest worker configuration.
- Installed runtime, outside those repositories: `.percy-vnext/src/acceptance.py`,
  `percy_vnext.py`, safety tests, wrapper, acceptance guide, and LaunchAgent PATH;
  Lyla's Percy adapter and contract tests. These edits are not a canonical source
  release. No commit, push, public visibility change, or production deployment
  was performed.

Final state: **NOT READY for combined public release / production certification**.
Working local implementation and the checks above are real; remaining engineering,
credentials, release evidence, and physical validation are explicitly incomplete.
