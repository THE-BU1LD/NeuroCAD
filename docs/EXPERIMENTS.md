# Experiments

- Historical controlled suite: `../research/runs/NC-RUN-2026-09-03-FULL/`.
  Development evidence only: producing source is unbound and 181 kernel artifacts
  were resumed.
- Audit prompt challenge: 24/24 cases passed. Dataset and raw records are under
  `../research/benchmarks/` and `../research/results/`. It was authored after code
  inspection, so it is not independent confirmation.
- Fresh Astra development suite: 30 compiler tasks, 24 IR programs, 16 malformed
  inputs, 12 constraint interventions, 12 edits, and seven fresh kernel renders
  passed with artifact reuse disabled. It is dirty-tree development evidence.
- Independent confirmatory experiment: not run. The protocol cannot be frozen
  until an outside-authored dataset and compatible baseline are supplied.

Execution rules are in `../research/protocols/`.
