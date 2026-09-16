# NeuroCAD research closeout — 2026-09-16

This document narrows remaining work to evidence-backed closeout only. It does not reopen already-met research gates and it does not authorize access to blocked S3 outcomes.

## Already met according to `DEFINITION_OF_DONE.md`

- Truth recovery and claim boundaries
- Input contract
- Canonical representation / semantic validation
- Real OpenSCAD end-to-end path
- Geometry robustness on the selected full benchmark
- Evaluation with per-task records, baselines, paired tests, failures, hashes and conservative claims
- Production-path demo gate

## Remaining closeout work

### 1. Exact-revision integrity receipt

- Identify the exact revision intended as the release/research candidate.
- Run `pytest tests/test_integrity.py tests/test_research_provenance.py` on that exact revision.
- Record the exact Git SHA and command output in the evidence ledger.
- Do not substitute results produced from another branch/revision.

### 2. External CI receipt

- Run/verify Python 3.10–3.12 CI on Linux, macOS and Windows for the exact candidate revision.
- Preserve workflow/run URLs and commit SHA.
- Verify the Linux OpenSCAD integration job on the same revision.

### 3. Security receipt

- Run Bandit and dependency audit against the exact release environment.
- Store machine-readable output when possible.
- Record tool versions, environment identity and exact revision.

### 4. Distribution receipt

- Build wheel and sdist from a clean exact revision.
- Install the exact generated outputs in a clean environment.
- Generate provenance binding artifact checksums to the Git SHA.
- Verify version metadata consistency.

### 5. External release evidence

Only after the exact-revision gates above are green:

- record exact Git SHA
- record CI URLs
- record anonymous/clean installer result
- record tag
- record artifact checksums
- record public release URL, if actually published

Do not fabricate any unavailable external receipt.

### 6. S3 scientific boundary

Keep `research/s3/PRE_OUTCOME_STATUS.json` blocked until the preregistered candidate-pool freeze, pilot selection, authorization, provider/model pinning and budget approval requirements are genuinely satisfied.

No S3 learned outcome may be accessed, summarized or used to tune the protocol before authorization. If the protocol changes after outcome visibility, create a new version/experiment rather than rewriting the frozen one.

## Closeout acceptance rule

NeuroCAD is research/release-complete only when all applicable gates refer to the same exact source revision. A result from another branch, local checkout or historical run is supporting context, not an exact-revision receipt.
