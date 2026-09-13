# Research Audit Checklist — VertexED

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/VertexED`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **scaffold**. Education product repository; research evidence must remain isolated from product claims.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **1001**
- Top extensions: .md:317, .mjs:253, .tsx:159, .ts:86, .js:60, .json:33, .sql:30, .png:22
- Marker counts: todo=2, placeholder=1154, stub=19, hardcoded=16, claim-language=54
- README excerpt: # VertexED  VertexED is a private-beta exam-prep workspace for planning, focused study, generated practice, evidence-linked answer review, notes, flashcards, and tutoring.  ## Overview  This project brings together AI assisted study utilities (notes, quiz, paper generator, answer reviewer, chatbot, study planner) in a single modern, accessible web app built with:  - React + TypeScript (Vite) - Tailwind CSS with a small layer of custom design tokens (HSL variables) for dark/light theming - Supabase (auth + data) - One Node.js Vercel Serverless Function with an explicit route registry  ## Key Features (current focus)  - Unified learner dashboard with measured weak-topic, retry, mock-review, and sync status - Personalized Exam Prep page using the learner's exam date, subjects, unfinished mocks, due retries, verified weak topics, and flashcard queue - Study Zone with timers, calculator, grap...

## Component Classification

| Classification | Evidence |
| --- | --- |
| scaffold | Education product repository; research evidence must remain isolated from product claims. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=1154, stub=19 |
| hardcoded shortcut | hardcoded/toy markers=16 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P0 | VertexED | Repository is classified as scaffold, not a complete research artifact. | Education product repository; research evidence must remain isolated from product claims. | Any paper, benchmark, or project-count claim based on this component would overstate the evidence. | Either demote the public claim to the observed evidence tier, or implement the missing method/data/evaluation path and retain reproducible results. |
| P1 | VertexED | Unresolved placeholder/stub markers require manual triage. | `PROJECT_STATUS.md:17` - - Account-scoped browser state, durable cloud learner state, retry queues and recoverable mock-exam drafts. Timed-exam answers no longer cross a browser-global handoff.; `README.md:20` - - Practice-paper generator with timed mock → answer review → scheduled retry handoff; `DEFINITION_OF_DONE.md:14` - | F6 | Paper generation, timed mock, answer handoff and rubric review finish without manufactured scores. | VERIFIED_LOCAL |; `AUDIT_REPORT.md:49` - | Learner persistence | Some activity, mock and retry state relied on browser storage or shared handoff keys. | Features were added independently before an account-scoped persisten; `TRUTH_MAP.md:23` - | Paper Maker and mock-exam handoff | **IMPLEMENTED + VERIFIED** | Deterministic paper contract tests; labeled Paper Maker controls added to golden journey | | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `EXECUTION_QUEUE.md:24` - State vocabulary: `TODO`, `RUNNING`, `BLOCKED`, `FAILED`, `VERIFYING`, `DONE`.
- `docs/PRICING_QUOTA_PRODUCT_CONTRACT.md:23` - | Free | $0 | numeric allowance TBD from beta evidence |
### placeholder
- `PROJECT_STATUS.md:17` - - Account-scoped browser state, durable cloud learner state, retry queues and recoverable mock-exam drafts. Timed-exam answers no longer cross a browser-global handoff.
- `README.md:20` - - Practice-paper generator with timed mock → answer review → scheduled retry handoff
- `DEFINITION_OF_DONE.md:14` - | F6 | Paper generation, timed mock, answer handoff and rubric review finish without manufactured scores. | VERIFIED_LOCAL |
- `AUDIT_REPORT.md:49` - | Learner persistence | Some activity, mock and retry state relied on browser storage or shared handoff keys. | Features were added independently before an account-scoped persisten
- `TRUTH_MAP.md:23` - | Paper Maker and mock-exam handoff | **IMPLEMENTED + VERIFIED** | Deterministic paper contract tests; labeled Paper Maker controls added to golden journey |
- `PROJECT_TRUTH.md:53` - | Timed mock completion represents mastery | Rejected | Completion now records no score | NEGATIVE/REMOVED | None | Preserve regression |
### stub
- `docs/FEATURE_CHECKLIST_2026-09-09.md:69` - - Generated output validation is not educational validation. The deterministic scaffold deliberately has no factual answer key; source-extraction questions are not an approved exam
- `docs/API.md:153` - source-bound scaffold with `generation.degraded: true` and a fixed `failureClass`.
- `docs/ULTIMATE_CODE_REVIEW_2026-09-07.md:9` - VertexED is a substantial private-beta exam-preparation workspace. It has real authentication, server-side AI calls, persistence, timed practice, answer review, retry scheduling, a
- `public/study-guides/myp/chemistry/sessions/N24.md:260` - - If...the teeth are cleaned with mouthwash and toothpaste *(WTTE)* ✓
- `public/study-guides/myp/mathematics/sessions/N21.md:188` - - .2 correctly substitute their 8 into surface area formula of cylinder and SA of cone — 3 × π × 5 + 2 × π × 3 × their 8 + 1/3 × π × 3² × 4 OR 3.14...ACCEPT 150.79, 150.8
- `public/study-guides/myp/mathematics/sessions/M19.md:123` - - Notes: •¹ (A=)36.869... or 37 or (C=)53.13... or 53. •² sin(36.869...or 37) × (BC/28) = BC/28; or cos(53.13...or 53) × 28 = BC/sin(90); tan(53.13... or 53) = 28/BC; or their trig
### hardcoded
- `evals/README.md:91` - - Per-prompt tolerance bands (currently hard-coded 15%)
- `brand/MOTION.md:40` - Respect both operating-system reduced motion and the saved reduced-motion setting. Reduced motion stops active reactions, keeps the image still and disables the three play controls
- `brand/COPY.md:55` - The user named the optional workbook companion Apex, retiring the working name Vee. Use "Open Apex study shortcuts", "Show Apex" and "Hide Apex" for controls. "The book in your cor
- `brand/DESIGN.md:69` - Apex sits in the lower-right corner at 96px on desktop and 72px on mobile. His current form is an original 32-bit-style open workbook with cobalt covers, a triangular chest mark an
- `public/study-guides/myp/chemistry/sessions/N19.md:181` - **Question:** Select the hazard symbol that would be used on the Atomic Energy Lab toy if it were available today. (Four hazard symbols A–D shown — options included flammable, corr
- `public/study-guides/myp/chemistry/topics/stoichiometry.md:31` - A Slinky toy is made of 0.405 kg of iron. Calculate the number of moles of Fe. (M_Fe = 56 g mol⁻¹)
### claim
- `PROJECT_STATUS.md:5` - **Branch:** `codex/vertexed-publication-readiness`
- `VERTEXED_CONTROLLED_PILOT_PROTOCOL_202609.md:120` - If participants are minors or the pilot is run through a school, follow the school's required consent/guardian/administrative process. If results are later intended for formal huma
- `AUDIT_REPORT.md:5` - **Branch:** `codex/vertexed-publication-readiness`
- `PROJECT_TRUTH.md:9` - Current execution branch: `codex/vertexed-publication-readiness`
- `evidence/manifest.json:5` - "branch": "codex/vertexed-publication-readiness",
- `evidence/stage_12.md:9` - comparator, leakage controls, analysis, stopping rules and publication boundaries. The


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/VertexED` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P1 Checklist
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/VertexED` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/VertexED` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/VertexED` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/VertexED` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

