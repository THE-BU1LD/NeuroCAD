# Reviewer 3 — reproducibility/systems

## Summary
The maintained path is coherent and fail-closed, with unusually broad automated tests and a fresh-output research runner.

## Strengths
Pinned archival environment, source hashing, dirty-tree provenance, atomic artifacts, collision refusal, raw records, external-kernel checks, package isolation, and preserved negative history.

## Weaknesses and fatal concern
The retained FULL manifest predates these provenance controls: it has no source/lock scientific digest and reports 181 resumed kernel records. Current tests cannot retroactively authenticate it.

## Major concerns
No public exact revision/tag/CI receipt; no independent reproduction; no automated manuscript build; large 225 MB legacy archive complicates cloning though it preserves forensic evidence.

## Minor concerns
Several root compatibility modules remain outside the canonical `core/` package. Documentation had stale Git-state prose, now repaired.

## Missing experiments
Run the hardened full protocol from a clean published revision on Linux/Xvfb; compare deterministic hashes; anonymously install and reproduce elsewhere.

## Assessment
Novelty: low. Reproducibility infrastructure: strong, evidence status partial. Likely score: **5/10 borderline systems artifact, reject as research paper**. Confidence: **4/5**.

## Post-audit disposition
Repository mapping and canonical protocols now expose the boundary. External publication/replication remains required.
