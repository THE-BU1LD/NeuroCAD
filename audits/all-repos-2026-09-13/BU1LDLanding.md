# Research Audit Checklist — BU1LDLanding

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/BU1LDLanding`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **scaffold**. Product/portfolio landing site, not scientific evidence.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **785**
- Top extensions: .tsx:330, .ts:218, .md:103, .sql:64, .mjs:22, .json:12, <none>:9, .yaml:7
- Marker counts: todo=8, placeholder=321, stub=4, hardcoded=1, claim-language=85
- README excerpt: # The Bu1ld — Member Platform  An independent machine-learning research and building platform: projects, guides, papers, events, programs, and administration.  ## Stack  - TanStack Start + React 19 - Tailwind CSS v4 + shadcn UI - Supabase (auth, Postgres) with seed fallbacks for local demo mode only  ## Quick start  ```bash bun install cp .env.example .env bun run dev ```  Open `http://localhost:5173`  ## Environment  | Variable                         | Required           | Notes                                                          | | -------------------------------- | ------------------ | -------------------------------------------------------------- | | `VITE_SUPABASE_URL`              | for live auth/data | Supabase project URL                                           | | `VITE_SUPABASE_ANON_KEY`         | for live auth/data | anon/public key                                    ...

## Component Classification

| Classification | Evidence |
| --- | --- |
| scaffold | Product/portfolio landing site, not scientific evidence. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=321, stub=4 |
| hardcoded shortcut | hardcoded/toy markers=1 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P0 | BU1LDLanding | Repository is classified as scaffold, not a complete research artifact. | Product/portfolio landing site, not scientific evidence. | Any paper, benchmark, or project-count claim based on this component would overstate the evidence. | Either demote the public claim to the observed evidence tier, or implement the missing method/data/evaluation path and retain reproducible results. |
| P1 | BU1LDLanding | Unresolved placeholder/stub markers require manual triage. | `README.md:39` - 4. Sign up in the app, then promote your profile:; `DEMO_GUIDE.md:23` - update public.profiles set role = 'admin' where id = '<your-user-uuid>';; `DATABASE_SETUP.md:53` - SUPABASE_PROJECT_REF="your-project-ref" SUPABASE_DB_PASSWORD="..." bun run supabase:rls; `research/SCIENTIFIC_RISK_REVIEW.md:16` - - Placeholder partnerships, fabricated users, or unsupported institutional names.; `research/preflight/portfolio-preflight.md:24` - - Placeholder/source-risk matches: 21 | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `research/preflight/portfolio-preflight.json:239` - "?? TODO.md",
- `docs/SECURITY_REVIEW.md:63` - - `release:check` scans for setup copy, TODO, lorem, unsupported claims
- `Bu1ld-Landing/src/lib/date.ts:2` - if (!dateStr) return "TBD";
- `src/lib/portfolio-preflight.test.ts:21` - 'TODO replace SUPABASE_SERVICE_ROLE_KEY="super-secret-service-role-value" before release',
### placeholder
- `README.md:39` - 4. Sign up in the app, then promote your profile:
- `DEMO_GUIDE.md:23` - update public.profiles set role = 'admin' where id = '<your-user-uuid>';
- `DATABASE_SETUP.md:53` - SUPABASE_PROJECT_REF="your-project-ref" SUPABASE_DB_PASSWORD="..." bun run supabase:rls
- `research/SCIENTIFIC_RISK_REVIEW.md:16` - - Placeholder partnerships, fabricated users, or unsupported institutional names.
- `research/preflight/portfolio-preflight.md:24` - - Placeholder/source-risk matches: 21
- `landing-sites-release/registry.yaml:89` - primary_conversion: Register your team
### stub
- `landing-sites-release/claim-ledger.yaml:37` - usage: not asserted this pass
- `docs/AUDIT_EXECUTION_2026-09-06.md:28` - - 38 unreachable shadcn/member scaffold files.
- `docs/AUDIT_MASTER.md:147` - ### AUD-011 — Publications page is marketing stub
### hardcoded
- `Bu1ld-Landing/src/components/ui/sidebar.tsx:96` - // Adds a keyboard shortcut to toggle the sidebar.
### claim
- `BUILD_COMPLETION_REPORT.md:10` - - Privacy-aware academic metadata and publication import.
- `BUILD_PRODUCT_TRUTH.md:56` - - Public project, program, people, partnership, publication, and outcome data must come from real published rows. Code support does not prove real-world participation or research r
- `TRUTH_MAP.md:17` - | DOI publication metadata import | IMPLEMENTED + VERIFIED | Authenticated/rate-limited Crossref handler and normalization tests; live provider smoke pending |
- `research/VERIFIED_RESULTS_INDEX.yaml:21` - claim_not_allowed: final multi-seed publication result
- `research/NEMOTRON_AUDIT_REQUEST.md:48` - Return one of: approve Pass 2 queue, reorder queue, downgrade flagship, or block publication/product release.
- `research/SCIENTIFIC_RISK_REVIEW.md:5` - 1. **Novel intelligence mechanisms.** Genesis claims around developmental modular learning must be compared with dynamic sparse training, mixture-of-experts routing, progressive ne


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/BU1LDLanding` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P1 Checklist
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/BU1LDLanding` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/BU1LDLanding` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/BU1LDLanding` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/BU1LDLanding` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

