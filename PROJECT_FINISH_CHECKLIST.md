# Project finish checklist

Session: 2026-09-07. Completion requires fresh validation; historical results are context only.

## P0 — Build and release blockers

- [x] Read execution request and inspect current repository and unresolved portal merge.
- [x] Resolve nine portal conflict files while retaining lifecycle and upstream security work.
- [x] Reconcile dependency manifest and lockfile; install and validate merged portal.
- [x] Include lifecycle table in exhaustive database inventory and retain its authorization tests.
- [x] Run portal typecheck, lint, unit/contracts, browser tests, and production build.
- [x] Validate database suite against the integrated schema; record credential/environment blockers.
- [x] Verify current CAD tests, static checks, and installed workflow.
- [x] Record remaining publication/deployment blockers without claiming production success.

## P1 — Core product functionality

- [x] Trace member export, deletion request, cancellation, and administrator review after merge.
- [x] Trace installed CAD prompt → editable source → mesh → verification and invalid-input behavior.
- [x] Fix concrete failures found in those journeys with targeted regression checks.

## P2 — Reliability and validation

- [x] Preserve both synthetic-identity authorization checks and production certification workflow.
- [x] Check public/member UI loading, failure, accessibility, and persistence coverage.
- [x] Re-audit the final diff for regressions and inconsistent assumptions.

## P3 — Documentation and developer experience

- [x] Reconcile runtime, migration, and readiness documentation with integrated behavior.
- [x] Preserve the expansion backlog as proposals, not implemented capability claims.
- [x] Record exact commands/results and unresolved external requirements below.

## Evidence and blockers

No checks from an older revision certify the newly merged portal. Physical CAD
validation requires measurements from actual fabrication. Public release and
production migration require the corresponding external authorization and access.

## Validated session results

- Portal merge completed locally as `f0a9a50be0fbeca6870e6a65ff3401f542c833fe`; worktree clean.
- Resolved all nine conflict files, preserving membership lifecycle and upstream production hardening.
- Added account-deletion table to exhaustive RLS inventory and lifecycle suite to production certification workflow.
- Fixed member/admin lifecycle loading and retry states so backend failures cannot masquerade as empty data.
- Added two behavioral regression cases for loading and failed deletion-request reads.
- `npm ci`: succeeded; installation audit reported zero vulnerabilities.
- `npm run typecheck`, `npm run lint`: passed.
- `npm test`: 6 toolchain tests, 75 component tests, 20 Node contract tests passed.
- `npm run test:e2e`: 11 Chromium/public accessibility tests passed. These do not establish live authenticated behavior.
- `npm run build`: passed using disclosed fixture public configuration; final receipt identifies `f0a9a50`.
- CAD `python -m pytest -q`: 334 passed; the HTTP test was blocked by sandbox socket permissions. That test passed separately with local socket permission (335 distinct tests covered).
- CAD Ruff passed; mypy passed across 56 source files; installed wheel `pip check` passed.
- Installed-wheel demo executed from `/private/tmp`: plate, cylinder, enclosure, independent verification, and deliberate rejection passed. Evidence: `.tmp-release-work/finish-session-demo-20260907/DEMO_RECEIPT.json`.
- Re-audit: no migration changes relative to the prior locally certified schema; final portal build identifies merged source; no unresolved Git conflicts.

## External work and scope

Fresh database certification used the pinned Supabase Postgres image from the
earlier receipt in an isolated local VM. All 12 migrations applied, the expanded
two-identity matrix passed, and the lifecycle suite passed 23/23 checks. Both
transactions rolled back; zero synthetic profiles and deletion requests remained.
Logs and checksums: `.tmp-release-work/portal-finish-f0a9a50/`.
The initial bootstrap attempt used the image's restricted `postgres` role and
failed before changes; the successful replay used its `supabase_admin` role.
No production database was accessed.

- Public CAD release remains unpublished: reconcile canonical history, obtain exact-revision external CI, publish tag/artifacts, and verify anonymous installation.
- Portal production deployment and migration require canonical service access; then run production RLS and controlled two-member authentication workflows.
- Physical-fit claims require actual printed parts and measured results under `docs/PHYSICAL_VALIDATION_PROTOCOL.md`.
- The 109-item expansion backlog includes optional future and research work. It is not marked complete or treated as a current release promise.

Final verdict: **NOT READY — SPECIFIC BLOCKERS REMAIN** for the combined public
release and live membership launch. Local integration and the checks above pass;
external CI/public installation, production deployment/authentication, and physical
fit acceptance remain open. The operating checklist is complete for executable
local work; it does not certify the optional expansion backlog.
