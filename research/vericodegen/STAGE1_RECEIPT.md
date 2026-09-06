# VeriCodeGen Stage 1 development-smoke receipt

**Status:** COMPLETE — ENGINEERING/PLUMBING EVIDENCE ONLY  
**Merged commit:** `6e04ecf6d2f8633da2f19dcff251239307520d00`  
**CI workflow run:** `33353180757`  
**Environment:** GitHub Actions Ubuntu 24.04, Python 3.11.16, OpenSCAD 2021.01

## What was exercised

The Stage 1 development smoke executed three scripted development fixtures through both predeclared paths:

- direct OpenSCAD;
- structured `DesignGraph -> design_to_scad -> OpenSCAD`.

Both arms were compiled with the real OpenSCAD CLI to STL and evaluated from the final artifact with the same shared mesh verifier. One development fixture intentionally forced a first-attempt failure in each arm so retry accounting was exercised symmetrically.

## Receipt

- task count: 3;
- arms: 2;
- final arm/task cells: 6;
- passing final cells: 6;
- total attempts: 8;
- cells using the forced retry: 2;
- Stage 0 verifier regression tests in the workflow: 6 passed;
- retained workflow artifact files: 23;
- workflow artifact ZIP SHA-256: `5a603fb2412cfe3f38b623e382dc69ce97fa5ed03ea784d25bd58362a4aed035`;
- workflow artifact ID: `9744281057`.

## Defects found and fixed during Stage 1

1. **STL topology representation:** raw STL imports with `process=False` can repeat vertex coordinates per facet. Counting connectivity by raw vertex index therefore made a geometrically closed STL box appear disconnected and non-watertight. The verifier now performs auditable vertex deduplication on a copy used only for topology checks; raw geometry remains the source for extents, bounds, and volume.
2. **CI test dependency:** the first Stage 1 workflow omitted `pytest`; the workflow now installs it explicitly.
3. **Module execution:** invoking `research/vericodegen/dev_smoke.py` by file path removed the repository root from Python's import path. CI now executes `python -m research.vericodegen.dev_smoke`.

All three fixes were exercised by the final successful run.

## Scientific boundary

This receipt is **not evidence that the structured arm is better than direct generation**. The fixtures are scripted, tiny, and development-only. There were no language-model calls, no paid API calls, no frozen-pilot outcome, and no primary-benchmark outcome.

The historical typed-parser causal/mechanism claim remains falsified. Nothing in Stage 1 changes that result.

## Next gate

Stage 2 may proceed only after a frozen pilot run manifest names the benchmark manifest hash, pilot task IDs, exact provider/model, decoding settings, retry policy, prompt-template hashes, verifier hash, git commit, seed set, and cost cap. External execution remains blocked until that manifest is explicitly authorized.
