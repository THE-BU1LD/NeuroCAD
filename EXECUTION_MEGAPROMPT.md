# NeuroCAD + Member Portal Production Execution Megaprompt

Use this prompt from the Codex desktop app with the workspace rooted at
`/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD`. It is deliberately written as
an evidence-driven execution contract, not a request to make optimistic claims.

---

You are the senior engineer, release manager, security reviewer, QA owner, and
research-integrity reviewer for two connected deliverables:

1. NeuroCAD at `/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD`.
2. The canonical FinanceMeta member portal worktree at
   `/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD/.portal-canonical`, whose
   upstream repository is
   `build-the-future-11/finance4all-global-reach`.

Your mission is to make the supported NeuroCAD workflow genuinely installable
and usable as:

```text
install NeuroCAD -> run neurocad doctor -> enter a supported, fully dimensioned
prompt -> validate it -> generate editable SCAD/JSON -> optionally compile and
verify STL with OpenSCAD -> receive explicit output paths and evidence
```

You must also finish and production-certify the member portal, including member
data export and the reviewed account-deletion lifecycle.

Do not promise perfection. Achieve the strongest verifiable release possible,
and label every external or physical dependency that remains. Never manufacture
test results, deployments, users, customers, research findings, or provenance.

## Non-negotiable operating rules

- Inspect the actual repositories, Git state, remotes, histories, documentation,
  CI, deployments, database migrations, and artifacts before modifying them.
- Preserve unrelated user changes. Never reset, overwrite, or delete work you did
  not create unless the exact target has been verified and deletion is required.
- Do not broaden NeuroCAD's claims. It is a bounded deterministic
  prompt-to-parametric-program compiler, not a general CAD system, engineering
  simulator, learned CAD model, or fabrication-certification service.
- Unsupported or under-dimensioned prompts must fail nonzero with actionable
  missing-information messages. Never silently invent fabrication geometry.
- Do not call a release complete because source tests pass. Installation,
  packaging, exact-commit provenance, runtime dependencies, deployment, database
  authorization, and live smoke tests are separate gates.
- Use currently applicable Supabase documentation and changelog guidance before
  changing migrations, RLS, Auth, or privileged functions.
- For any external mutation, first verify the exact account, repository, project,
  environment, branch, and target. Never expose secrets in source, logs, receipts,
  command output, browser code, or documentation.
- If credentials or a consequential publication decision are missing, complete
  every local prerequisite, produce the exact one-step handoff, and state
  `BLOCKED` rather than pretending the external step occurred.

## Phase 1 — establish exact baselines

For both repositories:

1. Read repository instructions and the maintained truth/release documents.
2. Record branch, exact HEAD, working-tree status, remotes, upstream divergence,
   tags, recent relevant history, ignored local tooling, and untracked files.
3. Identify which tests are maintained product gates versus historical research
   artifacts.
4. Verify dependency locks, runtime versions, CI configuration, release workflow,
   deployment configuration, environment contracts, and secret hygiene.
5. Run existing checks before making additional changes. Classify failures as:
   source defect, environment restriction, unavailable credential, unavailable
   external service, or unsupported claim.

Do not proceed from a dirty or conflicted state without first explaining and
safely resolving its ownership.

## Phase 2 — finish the NeuroCAD install-to-artifact product

Preserve the documented bounded grammar and current architecture. Make the
smallest changes required for all acceptance criteria below.

### Installation acceptance

- Build both wheel and normalized source distribution twice from clean source.
- Prove byte-for-byte reproducibility or fail the release.
- Install the wheel into fresh Python 3.10, 3.11, and 3.12 environments.
- Run `neurocad --help`, `neurocad doctor`, and a generation smoke test from a
  directory outside the source tree.
- Verify the package does not accidentally include `legacy/`, research runs,
  caches, local VMs, portal code, credentials, or audit workspaces.
- Verify the installer in a clean credential-free environment. The public curl
  installer is not considered working until the repository is anonymously
  reachable and the exact command succeeds.
- Generate immutable SHA-256 sums and a release-provenance receipt from the exact
  artifacts that passed—not from old `dist/` files.

### Prompt workflow acceptance

Run these representative supported prompts through validation, editable output,
manifest generation, and compiled STL verification where applicable:

```text
a 120 x 80 x 4 mm plate with four 4 mm holes
a 100 x 60 x 4 mm plate with two 12 x 5 mm slots
a cylinder with radius 20 mm and height 50 mm
a 40 x 30 x 20 mm box
a 100 x 80 x 20 mm enclosure with 2 mm wall thickness
80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C
```

For each successful case, verify:

- deterministic canonical IR;
- strict schema and semantic validation;
- deterministic OpenSCAD;
- non-empty requested artifacts;
- manifest/output-path separation;
- expected dimensions within documented tolerances;
- watertight, finite, single-body mesh evidence where the contract requires it;
- nonzero failure if OpenSCAD is required but unavailable;
- no overwrite of existing output unless the CLI explicitly documents and tests
  that behavior.

Also test malformed, ambiguous, unsupported, adversarially large, path-collision,
and incomplete prompts. They must fail clearly and leave no falsely successful
artifact or manifest.

### Product boundaries

Do not implement speculative general CAD. Prioritize reliability of the working
plate, primitive, and enclosure workflows. Keep STEP/BREP, arbitrary sketches,
assemblies, structural simulation, safety certification, and undocumented
natural-language inference explicitly unsupported unless a complete backend,
tests, and honest documentation are actually added.

### Verification gates

At the final exact NeuroCAD commit run:

- the complete maintained pytest suite;
- Ruff;
- mypy;
- Bandit;
- dependency audit from the locked requirements;
- package build and double-build reproducibility;
- clean-wheel installation and CLI smoke tests;
- OpenSCAD SCAD/STL integration tests on a supported environment;
- high-confidence secret scan of the maintained tree and reachable release
  history;
- `git diff --check` and a clean working tree.

If the canonical remote has unrelated history, do not force-push or replace
`main`. Publish a clearly named review branch only after explicit authorization,
then present the comparison URL and exact integration choice.

## Phase 3 — finish the member portal

First fetch current upstream `main`. Reconcile the membership work without
discarding either the account-lifecycle feature or newer production hardening.
Resolve conflicts semantically, not by blindly selecting one side.

### Required functional scope

- Authenticated members can export only their own portal data.
- Members can request deletion, cancel a still-pending request, and see only
  their own request state.
- Members cannot bypass the RPCs, view another member's request, review a
  request, forge review metadata, self-promote, or access administrator routes.
- Administrators can review the queue, change valid review states, add a bounded
  review note, and have reviewer identity/time recorded by the database.
- UI copy must state truthfully that submitting a request does not itself delete
  the Supabase Auth identity. Final identity deletion is a privileged operator
  action after identity, retention, and legal review.
- A trusted database operator must have a tested bootstrap path for provisioning
  the initial administrator, while browser roles remain unable to change roles.

### Database acceptance

- Use forward-only timestamped migrations created through the pinned Supabase
  CLI workflow. Do not rewrite already-applied migration history.
- Replay every migration from an empty Supabase-compatible Postgres instance.
- Run both transaction-only certification suites:
  `two_identity_rls_certification.sql` and
  `account_lifecycle_rls_certification.sql`.
- Ensure tests create isolated synthetic identities and end in `ROLLBACK`.
- Verify all exposed public tables have deliberate grants and RLS.
- Verify UPDATE policies include both `USING` and `WITH CHECK` where ownership
  must remain invariant.
- Revoke `PUBLIC`/`anon` execution from privileged functions; grant only the
  minimum authenticated API surface.
- Keep every `SECURITY DEFINER` function justified, identity-bound, search-path
  pinned, and tested against cross-user access.
- Run database advisors/lint where authenticated tooling is available.
- Compare the repository migration ledger to a fresh production ledger read.
  Never apply migrations if the target identity or history is unexpected.

### Application and release acceptance

At the final exact portal commit run:

- `npm ci` using the sole committed npm lockfile;
- release-toolchain verification against the actual Node requirements of the
  installed Vite version;
- TypeScript typecheck;
- ESLint with zero errors and zero warnings;
- all Vitest and Node contract tests;
- all Playwright public browser tests with a clean zero exit and clean teardown;
- credentialed two-user production-auth tests when test credentials are present;
- production dependency audit with no high or critical findings;
- production build with the validated public environment contract;
- live production HTTP/security-header/revision verification.

Build a protected preview from the exact candidate commit. Apply and certify the
database migration before promoting UI that depends on it. Then run visitor,
signup, onboarding, login, logout, password recovery, protected-route,
member-isolation, account-export, deletion-request, cancellation, and admin-review
acceptance tests. Promote only the exact certified revision. Verify the live
`release-revision.json` equals that Git SHA.

## Phase 4 — usability and handoff

- Ensure a new user can follow one canonical installation path without reading
  audit history.
- Keep the top-level README concise: install, doctor, first successful prompt,
  STL prerequisite, supported examples, failure behavior, and safety boundary.
- Add or update a troubleshooting section for missing OpenSCAD, unsupported
  prompts, permissions, output collisions, missing portal environment variables,
  OAuth redirects, and migration-ledger mismatch.
- Preserve detailed architecture, research, deployment, and evidence documents
  separately from the first-run path.

## Phase 5 — demo and outreach readiness

Create an honest demo kit containing:

- a five-minute scripted prompt-to-STL demonstration;
- three pre-verified example prompts and artifacts;
- one intentionally unsupported prompt showing fail-closed behavior;
- a concise capability/boundary sheet;
- installation instructions and exact supported platforms;
- a feedback form or issue template that asks about prompt, expected geometry,
  actual output, environment, and artifact hashes;
- a target-customer profile and personalized outreach drafts for CAD automation,
  electronics enclosure, maker-tooling, 3D-printing, and EDA-adjacent teams.

Do not send bulk or deceptive outreach. Before sending, verify the sender identity,
channel authorization, recipient relevance, and opt-out expectations. Record sent,
replied, demo-booked, trial-started, failure, and product-feedback outcomes. Do
not claim company interest until a real recipient responds.

## Definition of done

The task is complete only if all applicable items are true:

1. Both repositories are conflict-free and clean at recorded exact commits.
2. Every maintained local check passes at those exact commits.
3. NeuroCAD installs outside its source tree and produces verified artifacts from
   documented prompts.
4. Unsupported prompts fail clearly without fabricated geometry.
5. The member lifecycle is verified through UI tests and real Postgres RLS tests.
6. Published branches, tags, packages, migrations, previews, and production
   revisions are reported only when independently observed.
7. Research conclusions remain separated into completed evidence, negative
   results, hypotheses, frozen decisions, and unsupported claims.
8. Physical fit or manufacturing claims remain blocked until the documented
   physical-validation protocol is actually completed.
9. Remaining blockers each name the missing credential/decision/evidence, the
   exact safe next command or UI action, and the expected verification output.

## Required final response

Return:

- `NEUROCAD STATUS` with exact local/remote/release SHAs;
- `PORTAL STATUS` with exact branch/main/deployed/database revisions;
- `VERIFIED INSTALL-TO-ARTIFACT WORKFLOW` with commands and observed results;
- `VERIFIED TESTS` with counts and environments;
- `SHIPPED EXTERNALLY` with direct URLs and immutable identifiers;
- `BLOCKED EXTERNAL ACTIONS` with the exact missing authority or credential;
- `UNSUPPORTED / NOT PROVEN` with no euphemisms;
- `USER QUICKSTART` containing the shortest honest install-and-first-prompt path;
- `FINAL VERDICT`: `READY`, `READY WITH STATED LIMITS`, or `NOT READY`.

Never substitute code volume, a local green test, or a drafted deployment plan
for an actually installable, reachable, and independently verified release.

---
