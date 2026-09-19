# Research Audit Checklist — FinanceMeta-Landing

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/FinanceMeta-Landing`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **scaffold**. Product/portfolio site, not a research repo.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **312**
- Top extensions: .tsx:120, .ts:60, .md:45, .sql:23, .json:17, .mjs:11, <none>:7, .py:6
- Marker counts: todo=2, placeholder=117, stub=1, hardcoded=1, claim-language=13
- README excerpt: # FinanceMeta landing and member platform  This workspace contains the FinanceMeta public landing, authenticated member platform, and evidence/research registry.  ## Surfaces  - Root: public landing and conversion surface. - `Finance4allLanding/`: public directories, Supabase Auth, onboarding, portal, applications, and admin. - `FinanceMetaLanding/`: operating registry and research experiment packages.  The landing never guesses the production member origin. Set `VITE_MEMBER_APP_URL` to a verified HTTPS member URL; otherwise production membership CTAs fail closed to on-page/contact paths. See `PROJECT_TRUTH.md` and `DEFINITION_OF_DONE.md` for exact release state.  ## Verify the landing  ```bash npm ci npm run release:check ```  ## Verify the member platform  ```bash cd Finance4allLanding npm ci npm run typecheck npm test npm run lint VITE_SUPABASE_URL=https://pnemeegkwyaicsbnbnmg.supabas...

## Component Classification

| Classification | Evidence |
| --- | --- |
| scaffold | Product/portfolio site, not a research repo. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=117, stub=1 |
| hardcoded shortcut | hardcoded/toy markers=1 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P0 | FinanceMeta-Landing | Repository is classified as scaffold, not a complete research artifact. | Product/portfolio site, not a research repo. | Any paper, benchmark, or project-count claim based on this component would overstate the evidence. | Either demote the public claim to the observed evidence tier, or implement the missing method/data/evaluation path and retain reproducible results. |
| P1 | FinanceMeta-Landing | Unresolved placeholder/stub markers require manual triage. | `FINANCEMETA_EXTREME_EXECUTION_MEGAPROMPT.md:158` - placeholder keys, service-role strings, TODO/FIXME/HACK, mock data, fake; `Finance4allLanding/README.md:27` - VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key; `Finance4allLanding/DEPLOYMENT.md:7` - `main` now fails closed when the browser Supabase configuration is missing, malformed, or placeholder-valued. A green GitHub Actions build does **not** prove that the Vercel projec; `Finance4allLanding/supabase/README.md:3` - Follow these steps to connect your FinanceMeta portal to Supabase.; `Finance4allLanding/supabase/config.toml:11` - # Schemas to expose in your API. Tables, views and stored procedures in this schema will get API | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `FINANCEMETA_EXTREME_EXECUTION_MEGAPROMPT.md:158` - placeholder keys, service-role strings, TODO/FIXME/HACK, mock data, fake
### placeholder
- `FINANCEMETA_EXTREME_EXECUTION_MEGAPROMPT.md:158` - placeholder keys, service-role strings, TODO/FIXME/HACK, mock data, fake
- `Finance4allLanding/README.md:27` - VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
- `Finance4allLanding/DEPLOYMENT.md:7` - `main` now fails closed when the browser Supabase configuration is missing, malformed, or placeholder-valued. A green GitHub Actions build does **not** prove that the Vercel projec
- `Finance4allLanding/supabase/README.md:3` - Follow these steps to connect your FinanceMeta portal to Supabase.
- `Finance4allLanding/supabase/config.toml:11` - # Schemas to expose in your API. Tables, views and stored procedures in this schema will get API
- `Finance4allLanding/src/test/auth-recovery.test.tsx:8` - vi.mock("@/lib/supabase", () => ({
### stub
- `PROJECT_EXECUTION_REPORT_2026-09-06.md:17` - the ecosystem production-ready. The portal also contained dead scaffold and
### hardcoded
- `Finance4allLanding/src/components/ui/sidebar.tsx:78` - // Adds a keyboard shortcut to toggle the sidebar.
### claim
- `FINANCEMETA_SITE_RELEASE_REPORT.md:15` - - Complete program-detail pages backed by a database-enforced publication contract and administrator authoring fields.
- `DEFINITION_OF_DONE.md:38` - Builds must fail on TypeScript errors or invalid public Supabase configuration. The landing must remain useful when the member origin or analytics service is unavailable. Analytics
- `FINANCEMETA_COMPLETION_REPORT.md:48` - - Live Supabase: program publication migration `015` applied; incomplete active publication is rejected and complete public fields are anonymously readable.
- `FinanceMetaLanding/SEPTEMBER_2026_COMMAND.md:60` - 7. Public claims must be evidence-level tagged internally before publication.
- `FinanceMetaLanding/OPERATING_SYSTEM_2026.md:110` - - publication of methodology and aggregate outcomes.
- `FinanceMetaLanding/templates/partner_crm_record.md:47` - Record only operating facts needed to manage the relationship. Keep private email contents outside a public evidence repo unless publication is explicitly appropriate.


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.


## P0 Checklist
- **WHAT:** Repository is classified as scaffold, not a complete research artifact.
  **WHY:** Any paper, benchmark, or project-count claim based on this component would overstate the evidence.
  **HOW:** Either demote the public claim to the observed evidence tier, or implement the missing method/data/evaluation path and retain reproducible results.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FinanceMeta-Landing` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P1 Checklist
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FinanceMeta-Landing` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FinanceMeta-Landing` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FinanceMeta-Landing` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FinanceMeta-Landing` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

