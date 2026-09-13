# Research Audit Checklist — Research-Pilot

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/Research-Pilot`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Workflow web prototype with template markers and checked-in environment risk.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **143**
- Top extensions: .tsx:112, .ts:11, .json:7, .js:2, .html:1, .local:1, .lockb:1, .md:1
- Marker counts: todo=0, placeholder=141, stub=0, hardcoded=15, claim-language=11
- README excerpt: # Research Muse  Research Muse is a student research workspace spanning idea development, literature review, methodology planning, analysis, writing feedback, integrity checks, ethics review, and export.  ## Run locally  Requirements: Node.js 20 or newer and npm.  ```sh npm ci npm run dev ```  Production verification:  ```sh npm run lint npm run build ```  ## Backend modes  Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` in `.env.local` to use Supabase. When either value is absent, the app explicitly runs in local demo mode: authentication and project state remain in that browser's local storage, server functions are unavailable, and the data is not collaborative or durable.  Environment files are ignored. Do not commit credentials or deployment-specific values.  ## Capability boundary  The workspace provides guided client-side tools and user-interface flows. Its sample profe...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Workflow web prototype with template markers and checked-in environment risk. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=141, stub=0 |
| hardcoded shortcut | hardcoded/toy markers=15 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | Research-Pilot | No retained result artifact detected. | No obvious result/run/metrics path was found. | The repository cannot support empirical claims without rerunning or trusting prose. | Commit frozen result manifests with seeds, hashes, configs, logs, and tables. |
| P1 | Research-Pilot | Unresolved placeholder/stub markers require manual triage. | `supabase/functions/ai-writing-feedback/index.ts:39` - rewrite: "State your question, your variable(s), and the reason the topic matters in one clear opening paragraph.",; `src/components/ui/empty-state.tsx:38` - description: "Create your first research project and let us guide you through every step.",; `src/components/ui/smart-prompt.tsx:22` - placeholder?: string;; `src/components/ui/command.tsx:47` - "flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",; `src/components/ui/onboarding-overlay.tsx:30` - description: "Your all-in-one research companion. Let's take a quick tour of what you can do here.", | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |
| P1 | Research-Pilot | Claim language appears without retained evidence. | `supabase/functions/generate-ideas/index.ts:69` - realWorldImpact: "Gives a stronger statistical angle and can support a publication-style writeup.",; `src/components/ui/empty-state.tsx:90` - "Filter by publication year for recent work",; `src/components/ui/onboarding-overlay.tsx:54` - description: "Upload CSV files, run statistical tests, and create publication-ready visualizations in one click.",; `src/components/landing/FeaturesSection.tsx:45` - description: "Upload data, run statistics, and create publication-ready charts instantly.",; `src/components/workspace/ExportCenter.tsx:80` - description: "Conference poster layout", | Novelty or SOTA framing may be unsupported. | Bind each claim to a checked result, citation, proof, or explicit limitation. |


## Marker Evidence

### todo
_No examples found in scanned text files._
### placeholder
- `supabase/functions/ai-writing-feedback/index.ts:39` - rewrite: "State your question, your variable(s), and the reason the topic matters in one clear opening paragraph.",
- `src/components/ui/empty-state.tsx:38` - description: "Create your first research project and let us guide you through every step.",
- `src/components/ui/smart-prompt.tsx:22` - placeholder?: string;
- `src/components/ui/command.tsx:47` - "flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
- `src/components/ui/onboarding-overlay.tsx:30` - description: "Your all-in-one research companion. Let's take a quick tour of what you can do here.",
- `src/components/ui/workflow-guide.tsx:34` - title: "1. Brainstorm Your Topic",
### stub
_No examples found in scanned text files._
### hardcoded
- `src/components/ui/sidebar.tsx:78` - // Adds a keyboard shortcut to toggle the sidebar.
- `src/components/workspace/WorkspaceSidebar.tsx:46` - { id: "writing", label: "Writing Studio", icon: PenTool, description: "Draft & refine", color: "hsl(0 85% 55%)", tip: "AI helps you write better, not write for you", shortcut: "1" 
### claim
- `supabase/functions/generate-ideas/index.ts:69` - realWorldImpact: "Gives a stronger statistical angle and can support a publication-style writeup.",
- `src/components/ui/empty-state.tsx:90` - "Filter by publication year for recent work",
- `src/components/ui/onboarding-overlay.tsx:54` - description: "Upload CSV files, run statistical tests, and create publication-ready visualizations in one click.",
- `src/components/landing/FeaturesSection.tsx:45` - description: "Upload data, run statistics, and create publication-ready charts instantly.",
- `src/components/workspace/ExportCenter.tsx:80` - description: "Conference poster layout",
- `src/components/workspace/IdeaGenerator.tsx:204` - options: ["Science fair", "Publication", "Learning", "College apps"],


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
- **WHAT:** No retained result artifact detected.
  **WHY:** The repository cannot support empirical claims without rerunning or trusting prose.
  **HOW:** Commit frozen result manifests with seeds, hashes, configs, logs, and tables.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Research-Pilot` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Research-Pilot` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Claim language appears without retained evidence.
  **WHY:** Novelty or SOTA framing may be unsupported.
  **HOW:** Bind each claim to a checked result, citation, proof, or explicit limitation.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Research-Pilot` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Research-Pilot` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Research-Pilot` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Research-Pilot` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

