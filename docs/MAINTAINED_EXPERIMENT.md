# Maintained NeuroCAD experiment

NeuroCAD has one maintained, outcome-safe experiment entry point:

```bash
python scripts/run_maintained_experiment.py
```

The runner executes the VeriCodeGen Stage-1 scripted plumbing smoke from a **clean Git checkout** and writes a timestamped result directory under `out/maintained_experiment/`.

Each run produces `run_receipt.json` containing:

- exact Git commit and clean/dirty state;
- UTC timestamp;
- exact executed command;
- Python/platform and OpenSCAD identity;
- experiment-source SHA-256;
- explicit seed policy;
- Stage-1 summary metrics;
- paths and SHA-256 digests for the summary, attempts, finals, stdout, and stderr artifacts;
- process exit status;
- the scientific claim boundary.

To choose an explicit result directory:

```bash
python scripts/run_maintained_experiment.py --outdir out/review-run-001
```

## What this run means

This command intentionally runs only the maintained VeriCodeGen **Stage-1 scripted development fixtures**. It is engineering evidence for experiment plumbing, OpenSCAD compilation, shared verification, retry accounting, and provenance capture.

It is **not** a language-model benchmark, does not authorize Stage-2 provider calls, does not support a VeriCodeGen-superiority claim, and does not change the historical typed-parser result from falsified / validation-dominant. Outcome-bearing Stage-2 execution remains gated by issues #21 and #22.

Archived or broken historical experiments are intentionally excluded from this runner.
