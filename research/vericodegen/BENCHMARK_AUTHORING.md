# VeriCodeGen benchmark authoring and freeze procedure

**Status:** pre-outcome methodology. No Stage 2 model execution is authorized by this document.

## Scientific boundary

The historical NeuroCAD typed-parser mechanism claim remains falsified. The benchmark described here evaluates the new VeriCodeGen successor hypothesis only.

The final held-out benchmark must be frozen before any Stage 2 outcome is inspected. Once the evaluated provider/model/version is selected, that evaluated model must not author, rewrite, filter, rank, or repair held-out tasks. Human reviewers may correct objective authoring defects before freeze, but every such correction must happen before the benchmark hash is finalized.

## Final benchmark target

Freeze exactly **120 tasks**:

- 40 `in_distribution` tasks;
- 40 `compositional` tasks;
- 40 `ood_constraint_stress` tasks.

IDs must be the contiguous sequence `VCG-001` through `VCG-120`. Every task must include at least one machine-checkable hard constraint and at least one semantic rubric criterion.

Do not put development prompts, Stage 1 fixtures, tutorial examples, or previously inspected model failures into the final held-out JSONL.

## Authoring review

Before freeze, review every task for:

1. unambiguous units and dimensions;
2. machine-checkable constraints that the shared verifier actually supports;
3. semantic rubric language that does not reveal an implementation template;
4. no dependency on external assets, imports, fonts, images, or files;
5. no exact duplicate prompt after normalization;
6. no near-duplicate prompt at the frozen token-Jaccard threshold;
7. balanced task-family counts;
8. no task copied from repository examples/tests or the Stage 1 development fixtures;
9. no impossible or internally contradictory hard constraints;
10. no post-outcome editing.

## Freeze command

Prepare an authoring JSONL outside the final frozen path, then run:

```bash
python -m research.vericodegen.benchmark_freeze freeze \
  path/to/authored_candidate.jsonl \
  --schema research/vericodegen/benchmark_schema.json \
  --output-jsonl path/to/frozen_benchmark.jsonl \
  --output-manifest path/to/frozen_benchmark.manifest.json \
  --expected-total 120 \
  --expected-per-family 40 \
  --near-duplicate-threshold 0.88
```

The command fails closed on malformed tasks, non-contiguous IDs, family imbalance, exact normalized duplicates, near duplicates, invalid ranges/bounds, or missing hard constraints. The canonical frozen JSONL is sorted by prompt ID and hashed byte-for-byte.

Record both the benchmark manifest hash and its embedded benchmark/schema hashes in the Stage 2 run record. Do not regenerate the final benchmark after any model outcome is viewed.

## Pilot selection

Stage 2 uses a small predeclared stratified subset to expose runtime/integration defects without opening the full benchmark. Select it deterministically from the frozen benchmark:

```bash
python -m research.vericodegen.benchmark_freeze select-pilot \
  path/to/frozen_benchmark.jsonl \
  --per-family 4 \
  --selection-salt '<frozen public selection salt>' \
  --output path/to/stage2_pilot_selection.json
```

This selects 12 tasks total, four from each family, using SHA-256 ranking rather than Python RNG state. Freeze and hash the selection file before any Stage 2 model call.

The Stage 2 manifest must contain the exact selected IDs and the SHA-256 of the selection file. Do not swap pilot tasks after failures are observed.

## Prompt freeze

Render and hash both arm templates before execution:

```bash
python -m research.vericodegen.prompt_freeze \
  research/vericodegen/prompt_bundle_v1.json \
  --repository-root . \
  --output-dir out/vericodegen_prompt_freeze
```

The shared task rules come from one common bundle. The arm difference is limited to the treatment-defining output contract: direct OpenSCAD versus the new `vericodegen-structured-v1` JSON schema.

The runner owns OpenSCAD fragment resolution for both arms. Direct outputs that set `$fn`, `$fa`, `$fs`, import external assets, or use markdown fences are rejected rather than silently repaired. Structured outputs are strict JSON and compile through the new research-only structured-spec validator/`DesignGraph` path.

## Analysis freeze

`analysis_plan_v1.json` predeclares:

- paired unit: prompt × seed;
- primary endpoint: Hard Verifiability Rate;
- contrast: structured minus direct;
- exact two-sided McNemar test;
- 95% paired percentile-bootstrap confidence interval;
- fixed bootstrap seed and replicate count;
- failures/timeouts/retry exhaustion as HVR failures;
- secondary endpoints as descriptive/exploratory only.

The Stage 2 manifest pins the analysis-plan SHA-256 before execution.

## Stage 2 execution gate

The current manifest protocol is `vericodegen-stage2-v2`. Execution remains blocked until all of the following are present and frozen:

- benchmark manifest SHA-256;
- deterministic pilot selection SHA-256 and task IDs;
- structured-output schema SHA-256;
- shared verifier SHA-256;
- analysis-plan SHA-256;
- direct, structured, and prompt-receipt hashes;
- exact provider and model identifiers;
- decoding parameters and seed list;
- symmetric retry policy with no human correction;
- exact OpenSCAD version, common fragment resolution, and compile timeout;
- retention of raw outputs, failed trials, and compile logs;
- git commit;
- exact maximum-call ceiling;
- cost cap;
- explicit `authorized=true` in a separately reviewed frozen manifest.

Until then, `research/vericodegen/stage2_run_manifest.example.json` must remain `authorized=false` and is intentionally non-executable.

## Claim gate

Stage 1's 6/6 development fixtures prove only that the engineering path can run. They are not model evidence. A Stage 2 pilot is still exploratory and is primarily for runtime/cost/integration defects. The full scientific claim gate remains Stage 3 on the frozen benchmark, followed by verifier audit, OOD/compositional reporting, retained negative evidence, and a clean reproduction.
