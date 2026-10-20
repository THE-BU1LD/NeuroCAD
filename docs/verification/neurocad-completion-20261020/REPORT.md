# NeuroCAD bounded completion candidate receipt

Status: focused local engineering verification passed; heavy, hosted, physical,
independent, Kaggle, release, and new-research gates remain open.

The candidate integrates three preserved product successors on top of the current
merged baseline: source-bound fit studies, evidence-bound cutout revisions, and
protected-interface/change-impact contracts. It also retains the current Feature
IR fail-closed repair.

## Local verification

```text
23 passed - fit study and fit sample
5 passed  - fit revision
26 passed - interface contract and Feature IR
Ruff: PASS
MyPy: PASS (5 changed source files)
git diff --check: PASS
Physics v2 desktop LaTeX compile: PASS
Physics v2 committed PDF visual review: PASS (6/6 pages)
Final compiled-aperture/profile-lock regression: PASS (11 tests, Ruff, MyPy)
```

An earlier combined test command timed out at the command wrapper's 30-second
ceiling without a terminal summary and is not counted. The identical cohort was
then split into complete bounded batches. The first attempted command referenced
an absent `.audit-venv`; no tests were collected in that attempt.

A final comparison with the prior session record exposed an unverified patch that
had not persisted in its worktree: nominal connector locks did not bind the
manufacturing profile or profile-compensated aperture. The current successor now
does so, and a connector-only regression proves that a profile-induced compiled
opening change is rejected.

## Resource admission

The latest sampled free plus speculative memory was approximately 331 MiB, below
the 512 MiB repository floor, and pageouts increased during the session. Full,
native, package, fresh-install, security and scientific workloads were therefore
not run locally. Existing hosted workflows are separately blocked before runner
allocation by the account billing/Actions spending-limit condition.

The integrated payload was committed locally as `3030ea5`, followed by verified
compiled-aperture correction `0fff2be`. A push of the earlier state to private remote
`build-the-future-11/NeuroCAD`, branch `codex/neurocad-perfect-20261020`, was
rejected by managed external-transmission review pending explicit approval of
that exact destination and payload. The remote branch therefore remains at
`8133960`; no workaround or post-correction push was attempted.

## Research and release boundary

No protected outcome was accessed. No training, provider call, paid compute,
Kaggle upload, physical experiment, participant activity, release, tag, or arXiv
submission was performed. The requested `arxiv.sty` asset is absent. The existing
complete Physics v2 paper remains unchanged and compiled successfully; it cannot
be repurposed as evidence for this product successor.

See `audit/neurocad_completion_20261020/AUDIT.md` for flaw-by-flaw disposition and
`audit/neurocad_completion_20261020/CONTRACT.json` for the bounded execution rules.
