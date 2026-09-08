# Project audit and execution backlog — 2026-09-08

## Scope and evidence

Inspected local NeuroCAD `00617bd` and portal `f0a9a50`; both were clean before
this report. This pass inspected source, routes, hooks, integration contracts,
packaging, release identity code, historical evidence, and previous validation
records. It did not rerun the entire suite or recheck live production.

Previous-session evidence: 335 distinct CAD tests covered, Ruff and mypy passed;
portal 75 component + 20 contract + 6 toolchain tests, 11 browser/accessibility
tests, typecheck/lint/build passed. Fresh local replay applied 12 migrations,
passed the authorization matrix and 23 lifecycle checks, and rolled back fixtures.
See `../PROJECT_FINISH_CHECKLIST.md` and its referenced local artifacts.
These counts demonstrate the tested cases, not complete feature coverage.

Status: **Salvageable; working supported CAD alpha, incomplete public release and
production acceptance.** Verdict: **FIX**, preserving the working compiler.

## What is implemented well

- `core/ir.py`, `ir_parser.py`, schema, and exporters provide a real typed
  representation, semantic validation, deterministic serialization, and compilation.
- `core/enclosure.py`, `natural_language.py`, `project.py`, and `edit_language.py`
  implement bounded enclosure requirements and revisioned edits.
- `core/enclosure_verification.py` and `artifacts.py` independently check generated
  geometry and bundle contents; these are more substantial than file-existence checks.
- `core/calibration.py` records measurements and explicitly limits recommendations
  to a declared setup. `manufacturing.py` distinguishes approximate estimates.
- CLI collision refusal, negative tests, packaging checks, and installed demos
  are useful product reliability work.
- Portal authentication, database-backed content, lifecycle operations, RLS tests,
  and lazy-loaded routes are implemented. The merge conflicts are resolved.
- Frozen research records preserve negative findings and distinguish scripted
  plumbing tests from model experiments.

## Pseudocode, scaffolding, and actual limitations

| Surface | Classification | Evidence and consequence |
| --- | --- | --- |
| Maintained `core/` and CLI | Executable implementation | No TODO/FIXME/NotImplemented markers found in the targeted scan; this does not prove absence of defects |
| `legacy/python/cad_master_kernel_legacy_broken.py` | Abandoned incomplete implementation | Contains `NotImplementedError`; excluded from supported distribution |
| `legacy/python/cad_intelligence_core_allinone.py:STEPExporter` | Historical fake capability, now disabled | Explicitly raises rather than emitting misleading STEP; there is no supported STEP kernel |
| `legacy/generated/` | Unproven historical artifacts | File presence does not establish source provenance or correctness |
| `core/integrations/registry.py` Fusion/Onshape entries | Real file handoff, incomplete native integration | Explicitly state no native API operation/document generation; executable/credential detection is not integration success |
| `model/README.md` | Documentation, not trained model | No implemented trained model is established by this directory |
| VeriCodeGen Stage 1 | Real engineering scaffold | Scripted fixtures and real kernel execution; explicitly no model calls |
| Later research manifests | Planned/frozen experiment infrastructure | Require authorized, pinned execution; no outcome may be inferred |
| Process defaults and mass/cost estimates | Real heuristics/analytical aids | Not physical calibration, simulation, load certification, or guaranteed fit |
| Portal input `placeholder=` attributes | Ordinary UI hints | Not fake implementations; do not remove merely because keyword search finds them |
| FinanceMeta portal | Working separate domain application | Routes concern news, labs, pathways, events, and members; no CAD library/build-evidence user journey is implemented |

## Confirmed current findings

1. **Search completeness defect:** `usePortalSearch.ts` limits each table to 20/30
   rows before local filtering. A matching later row is invisible. Queries have
   no explicit ordering, so the subset is not a stable search index.
2. **Search failure masking:** the same hook ignores Supabase response errors;
   `PortalSearch.tsx` renders no results rather than a retryable backend failure.
3. **Search efficiency/selection limitation:** every changed query key can fetch
   six tables; there is no debounce in the inspected input/hook. Final truncation
   follows category append order, not a documented relevance ranking.
4. **Detail failure masking:** `pages/portal/labs/MetaLabs.tsx` renders
   "Project not found" for both a failed query and an absent project.
5. **Build provenance gap:** `scripts/release-revision.mjs` validates SHA syntax
   and falls back to Git HEAD without checking a dirty tree. A local changed
   build can therefore carry the unchanged HEAD identity. The last final build
   was clean, but the general path remains misleading.
6. **Queue scaling gap:** `useAccountLifecycle.ts:useAccountDeletionRequests`
   fetches the whole queue without explicit pagination. This is a boundedness
   concern, not evidence of current production slowness.
7. **Product integration gap:** the finance membership application is not a CAD
   frontend. Deploying it alone would not create the proposed CAD membership product.
8. **Evidence/documentation drift:** the historical truth ledger has frozen
   language saying there are no tolerancing/process aids, while current code has
   limited helpers. Preserve historical text, but add a dated supersession note.
   The prior operating checklist's "all executable local work" wording is too broad:
   findings 1–6 are new executable work.
9. **Release gates remain open:** local success does not establish public install,
   external CI, production auth, production migration state, or physical fit.

## Execution rules

`BUG` is supported by inspected source. `GATE` requires observed acceptance.
`REVIEW` is a targeted investigation, not a diagnosed defect. `EXTENSION` is new
scope. Every item below is unchecked; close it only with the stated verification.
Portal-relative paths refer to `.portal-canonical/`. Archive work must preserve
forensic evidence and must not weaken tests or security gates.

## P0 — Correctness and release readiness

- [ ] A01 BUG — `src/hooks/portal/usePortalSearch.ts`: move filtering before limiting using validated database filters or a reviewed invoker-rights search endpoint; test a matching record beyond row 30 and cross-member visibility. Outcome: complete bounded search over authorized records.
- [x] A02 BUG — search hook and `components/portal/PortalSearch.tsx`: handle response errors explicitly, distinguish partial results if supported, and offer retry; inject one-table and total failures and ensure neither displays an unqualified empty success.
- [x] A03 BUG — `pages/portal/labs/MetaLabs.tsx`: separate unavailable backend, forbidden/absent result, and loading states; verify failure → retry → detail recovery without changing permissions.
- [x] A04 BUG — `scripts/release-revision.mjs`, `write-release-revision.mjs`, release tests: require a clean checkout for release builds or record an explicit nonrelease dirty identity plus source digest; verify changed files cannot masquerade as the clean commit.
- [ ] A05 GATE — NeuroCAD canonical remote/history and `.github/workflows/`: prepare a reviewable publication branch preserving history; verify diff and exact-revision CI before changing public visibility.
- [ ] A06 GATE — `install.sh`, release workflow, `docs/PUBLIC_ALPHA_EVIDENCE_LEDGER.md`: publish immutable artifacts and test anonymous installation outside a checkout; record downloadable provenance and actual URLs.
- [ ] A07 GATE — portal workflows, `DEPLOYMENT.md`, `supabase/migrations/`: compare production ledger and schema, apply only required migrations, and run both authorization suites; retain source/target receipts.
- [ ] A08 GATE — `e2e-credentialed/two-member-auth.spec.ts`: run controlled production login, onboarding, logout, session separation, and persistence; require success against the intended deployed SHA.
- [ ] A09 GATE — lifecycle hook, Settings, Admin, migration functions: verify real export, deletion request, cancellation, administrator review, and operator deletion procedure; confirm downstream cleanup and retention behavior with disposable identities.
- [ ] A10 GATE — `docs/PHYSICAL_VALIDATION_PROTOCOL.md`, `core/calibration.py`: print supported coupons and enclosure parts, record measured dimensions and failed fits, and evaluate held-out parts before adding physical-fit claims.

## P1 — CAD main experience and mathematical quality

- [ ] A11 REVIEW — `core/natural_language.py`, prompt tests: collect representative first-user requests and report supported/rejected/incorrect outcomes; extend only reproducible grammar gaps with explicit syntax tests.
- [ ] A12 REVIEW — `core/enclosure.py`, CLI help: enumerate every advertised feature against executable examples; remove a claim or implement its missing path whenever the matrix disagrees.
- [ ] A13 REVIEW — `core/project.py`, `edit_language.py`: test multi-edit chains, stale revisions, invalid field edits, and recovery; require previous valid projects to remain usable after rejection.
- [x] A14 REVIEW — `core/enclosure_verification.py`: inject missing cutouts, misplaced holes, filled cavities, and incorrect lids; verify the independent checker rejects them rather than relying on generator metadata. Completed: four real-kernel fault cases pass; insertion plug/shoulder probes close the correct-bounds/wrong-lid gap. Bounded probes are not arbitrary surface-equivalence proof.
- [ ] A15 REVIEW — `core/manufacturing.py:_shell_volume`: quantify estimate error against compiled mesh volume across supported cutouts/lids/standoffs; expose approximation bounds or use mesh volume when available.
- [ ] A16 REVIEW — `core/engineering_math.py`: document units, applicability, and tolerance dependence assumptions next to API examples; validate analytical reference cases and unsuitable-input rejection.
- [ ] A17 REVIEW — `core/calibration.py`: exercise correlated/repeated measurements, outliers, sparse observations, conflicting fit outcomes, and setup changes; require disclosed uncertainty and rejection where evidence is insufficient.
- [ ] A18 REVIEW — `core/artifacts.py`, integration exchange verifier: fuzz malformed manifests, excessive depth/size, symlinks, missing/extra files, and stale verification; retain current fail-closed semantics.
- [ ] A19 REVIEW — `core/integrations/kicad_file.py`: test unsupported board outlines and ambiguous mounting features; require explicit mechanical review for connector positions and component heights.
- [ ] A20 GATE — `core/integrations/registry.py`, `handoff.py`: perform real imports into each advertised external application; label untested handoffs precisely until evidence exists.
- [ ] A21 EXTENSION — `project.py`, enclosure specification: add protected mounting/connector interfaces and show conflicts when edits move them; test geometry after both accepted and rejected edits.
- [ ] A22 EXTENSION — enclosure generation plus CLI: produce interface-only fit samples preserving final dimensions; verify sample and final model agree, then test with physical measurements.
- [ ] A23 EXTENSION — calibration and project revisions: connect measured sample outcomes to a reviewable compensated revision; verify nominal dimensions remain recoverable and compensation is not applied twice.
- [ ] A24 EXTENSION — typed constraints and preflight: add bounded uncertain dimensions and conflict explanations; verify satisfiable, impossible, and unknown cases without calling sampled checks formal proofs.

## P1 — Portal completeness and UX

- [ ] A25 REVIEW — search input/hook: debounce typing, cancel obsolete work where supported, and define relevance ordering; verify rapid input cannot display stale results and count requests before/after.
- [ ] A26 REVIEW — deletion queue hook/Admin: add cursor pagination and status filtering when justified by expected volume; test beyond one page without duplicates or omissions.
- [ ] A27 REVIEW — all portal hooks/pages: inventory response-error handling; replace confirmed error-as-empty paths with shared retryable status components; test affected user journeys.
- [ ] A28 REVIEW — `AuthContext.tsx`, ProtectedRoute, RoleGuard: test expired sessions, delayed profile retrieval, role changes, and hydration races; never authorize based only on UI state.
- [x] A29 REVIEW — auth context and query client owner: verify logout/account switching removes sensitive cached data; test A → logout → B under slow network without showing A's records.
- [ ] A30 REVIEW — `Settings.tsx`, `Admin.tsx`: test export and review failures, double submissions, long notes, pending states, and screen-reader labels; ensure retries do not create duplicate requests.
- [ ] A31 REVIEW — public and authenticated pages: run keyboard/mobile/zoom checks at representative widths, including dialogs and long content; record screenshots and focus behavior instead of relying solely on Axe.
- [x] A32 REVIEW — AppRouter and lazy-loaded pages: verify recovery from a failed chunk download after deployment; supply an accessible retry/reload path if absent.
- [ ] A33 REVIEW — forms and mutation hooks: compare client constraints with database constraints; test direct bypass attempts and duplicate requests, preserving server enforcement.
- [ ] A34 EXTENSION — CAD product/portal ownership: define whether FinanceMeta stays separate or hosts a CAD area; specify navigation, identity boundaries, and data ownership before adding tables or rebranding.
- [ ] A35 EXTENSION — after A34, new CAD project storage/API/routes: implement owner-isolated upload, revision history, verification, download, and returning-session access; test another member cannot read or mutate a private design.
- [ ] A36 EXTENSION — after A35, build evidence records: attach measured outcomes to exact design/process revisions and preserve failures; test evidence invalidation after material or geometry changes.

## P2 — Architecture, performance, security, and operations

- [ ] A37 REVIEW — `neurocad_cli.py` (923 lines): identify command-group boundaries and shared I/O validation; extract only when a change needs it, preserving exit codes and CLI compatibility.
- [ ] A38 REVIEW — `core/enclosure.py` (1,078 lines): map specification, validation, and generation ownership; isolate a cohesive responsibility only with existing behavior tests passing.
- [ ] A39 REVIEW — `core/research_suite.py` (1,225 lines): separate experiment orchestration from reusable checks if coupling impedes maintenance; preserve frozen outputs and protocol identities.
- [ ] A40 REVIEW — `DesignGraph`, canonical IR, adapters: document why both representations exist and their loss boundaries; test round trips before considering consolidation.
- [ ] A41 REVIEW — database list/search queries and migrations: measure realistic cardinalities and query plans; add indexes only for demonstrated access patterns, then compare latency and write cost.
- [ ] A42 REVIEW — `core/demo_server.py` and compiler subprocess boundary: check input/output budgets, timeouts, concurrent requests, cleanup, and local binding; verify oversized work is rejected with bounded resources.
- [ ] A43 GATE — package locks, `SECURITY.md`, CI: run fresh vulnerability and secret scans for the actual release revision; retain scanner versions and findings without printing secrets.
- [ ] A44 REVIEW — `.github/workflows/` in both repositories: verify least-privilege credentials, pinned actions, untrusted-input boundaries, and exact source binding; exercise failure paths without weakening gates.
- [x] A45 REVIEW — production database target validation: replace substring-only connection checks with parsed host/project identity checks where necessary; reject foreign targets that merely contain the expected project text.
- [ ] A46 GATE — `DEPLOYMENT.md`: document backup/restore and compatible rollback for app/schema changes; rehearse in an isolated environment and record recovery results.
- [ ] A47 REVIEW — application failure reporting: define actionable error identifiers and redacted diagnostics; exercise failures and confirm user data and credentials are absent from logs.
- [ ] A48 GATE — member retention/export/deletion documentation: establish accountable operational ownership and response procedures; verify published promises match implemented behavior.

## P2 — Research integrity and documentation

- [x] A49 DOC — `audits/HISTORICAL_TRUTH.md`: add a dated note distinguishing frozen historical deficiencies from today's limited calibration/math helpers; preserve refuted claims unchanged.
- [x] A50 DOC — `PROJECT_FINISH_CHECKLIST.md`: qualify its completed checklist as the previous session's scoped work and link new findings; avoid claiming all possible local work is exhausted.
- [ ] A51 DOC — README, RELEASE_STATUS, capability boundary, integration help: build a single current capability matrix linking each claim to code and acceptance evidence; mark native integrations unavailable until implemented.
- [ ] A52 GATE — `audits/CLAIM_LEDGER.md`, research manifests: trace each numeric claim to retained artifacts and unique experimental units; distinguish duplicated fixtures from independent observations.
- [ ] A53 GATE — release research workflow: rerun the complete required kernel/render path on the supported Linux/Xvfb environment; preserve the earlier macOS offscreen-render failure as environment-specific evidence.
- [ ] A54 GATE — VeriCodeGen/S3 manifests: retain frozen decisions, authorization requirements, provider/model pins, cost caps, and outcome separation before executing learned experiments.
- [ ] A55 REVIEW — `legacy/`, root compatibility modules, `MANIFEST.in`: verify archive exclusion and locate remaining imports; document deprecation before moving/removing any live compatibility surface.
- [ ] A56 DOC — research/product docs: publish a clear distinction between deterministic compiler evidence, trained-model claims, mathematical checking, and physical testing; do not claim scientific novelty from packaging quality.

## P3 — Optional extensions, not defects

- [ ] A57 EXTENSION — units/constraints: add selected mixed units with canonical normalization and dimension checks; verify equivalent requests produce equivalent geometry.
- [ ] A58 EXTENSION — constraint engine: propose minimal parameter repairs under declared locks and weights; independently revalidate and avoid unjustified global-optimality claims.
- [ ] A59 EXTENSION — component models: add plug, cable, and screwdriver envelopes for supported parts; verify insertion/access paths and explicit bend assumptions.
- [ ] A60 EXTENSION — fabrication: integrate one versioned slicer, retain actual settings/results, and fail clearly on unavailable executables; compare estimates with real jobs.
- [ ] A61 EXTENSION — geometry backend: add a bounded STEP/B-rep path with real solid construction and external round-trip import; never wrap a mesh or marker file in a STEP label.
- [ ] A62 EXTENSION — assembly models: introduce a small supported hinge/slider family with checked motion envelopes; state sampling limits and require physical acceptance where relevant.
- [ ] A63 EXTENSION — experiments: compare defined optimization objectives with simple baselines and independent feasibility checks before marketing improvements.
- [ ] A64 EXTENSION — user validation: observe representative users completing enclosure tasks and returning to edit them; measure interventions, task completion, failed fits, and repeat use.

## Top five next actions

1. A01–A02: fix complete, error-aware portal search. This is a current user-visible defect.
2. A03: separate project-detail backend failures from missing records. Small, testable recovery improvement.
3. A04: bind release receipts to actual source content. Prevent misleading deployment evidence.
4. A05–A09: complete public and production acceptance using the validated candidates.
5. A10 and A22–A23: complete one measured enclosure fit loop before expanding geometry breadth.

Do not implement all extensions at once. First close confirmed bugs and external
release gates, then use observed user and physical results to select extensions.
The full idea inventory remains `PRODUCT_EXPANSION_CHECKLIST.md`; this document
adds the specific audit findings and execution order.

## Execution record — 2026-09-08

Portal implementation is committed locally as `425ceb64e24a739a0413c0ea6a4e3716dfadf3b4`, with final TLS/cursor hardening in `3f370f021dfdf0b617cba22da567e66cae59287f`.

- A01/A25: implemented server filtering before limits, quoted/escaped filters, deterministic candidate ordering, title ranking, debounce, cancellation, and removal of the duplicate command-palette filter. Regression tests find row 40 and reject failed-category responses. A real PostgREST/RLS search acceptance run remains open; unit mocks do not prove hosted behavior.
- A02: backend errors now produce a retryable failure rather than an empty success.
- A03: project details distinguish failed retrieval from a missing record and provide retry.
- A04: release receipts refuse tracked or untracked source changes; clean-source production build succeeded.
- A26: cursor pagination (25 displayed rows), tied-timestamp ordering, load-more controls, and status filtering are implemented. A 53-row pagination regression passes; real-database concurrent-update coverage remains open.
- A28/A29: identity changes clear the query client; old profile responses cannot replace the new member's profile. Profile operations are time-bounded. A→B→logout regression passes. Full expired-token/production acceptance remains open under A28.
- A32: a render/chunk failure produces an accessible recovery screen with reload; injected failure test passes.
- A45: parsed direct/pooler identity checks replace substring acceptance; URL routing overrides/TLS bypasses and duplicate TLS parameters are rejected. Workflow requires TLS.
- A14: independent lid probes now check insertion plug material and four shoulder clearances. Missing cutouts, moved holes, filled cavities, and a same-bounds solid slab substituted for a lid are rejected in real-kernel tests.
- A44: repaired four silently skipped CI steps: matrix entries use patch-pinned versions but type/security/sdist/upload conditions compared with `3.12`. Prefix conditions now match exactly one matrix entry; four regression tests protect reachability. The CI workflow is included in the sdist so these tests retain their input. Remote execution and the broader workflow review remain open.
- A49/A50: historical-versus-current calibration capability and previous-session completion scope are corrected without erasing negative evidence.
- A22: implemented `neurocad enclosure fit-sample` using the existing compiler's cutout dimensions and compensation, with source hash/revision metadata, explicit flat orientation, collision refusal, and bounded margins. Fourteen tests cover faces, shapes, errors, source identity, real mesh volume, and CLI behavior. Physical acceptance remains open, so the overall item is not checked.

Validation observed in this session:

- Portal: typecheck and lint pass; 81 Vitest tests, 23 Node contract tests, and 6 toolchain tests pass. The intentional error-boundary fixture logs its injected exception but the test passes.
- Chromium/public accessibility suite: earlier run passed 11 tests. Final-source rerun reported all 11 cases passed but stalled during worker shutdown; interrupted after 4.4 minutes (exit 130), so the final command is not a clean pass. Investigate local browser-worker teardown and rerun before release. These tests do not certify authenticated production UI.
- Clean portal production build: passes with fixture public config and final release identity `3f370f0`.
- `npm audit --omit=dev --audit-level=high`: zero reported vulnerabilities.
- CAD final source: full suite 357 passed; complete CI-scope Ruff and Bandit passed; mypy passed for 57 source files. Targeted fit-sample suite: 14 passed; enclosure-product suite including four injected faults: 19 passed.
- Wheel/sdist isolated builds succeeded and distribution inspection accepted 44 wheel members and 181 sdist members. Initial no-isolation build correctly failed because the reused test environment had older build tools; isolated pinned tools resolved that environment mismatch.
- Final wheel/sdist rebuild succeeded; distribution inspection accepted 44 wheel members and 185 sdist members. Reinstalled final wheel outside source produced a verified coupon STL: extents 22×17×2 mm, material volume 580 mm³, one watertight body. Artifacts are local under `.tmp-release-work/finish-audit-20260908-final-dist`, not published releases.
- Dependency advisory scan of `requirements-research.lock`: PyPI timed out at 15 and 45 seconds; OSV fallback completed with no known vulnerabilities. Full-history high-confidence secret-pattern scan returned no matches; this is not an exhaustive secret audit.

Incomplete means incomplete: all other unchecked items retain their original
requirements. They are not automatically classified as external. Remaining local
extensions/reviews include protected interfaces, uncertainty/repair solvers,
CAD portal storage and evidence workflows, broader process/assembly support,
additional operational testing, and full checklist-wide acceptance. External
release, production credentials, physical measurements, and authorized research
runs are separate blockers. This execution record does not assert that the entire
64-item audit or 109-item expansion backlog is complete.

Filter escaping was checked against the official PostgREST URL grammar:
https://docs.postgrest.org/en/v16/references/api/url_grammar.html
