# Development protocol

1. Run compile/import, unit tests, Ruff, mypy, and `pip check`.
2. Run a 30-task, 8-invalid-case, one-kernel-sample source-bound suite into a new
   temporary directory.
3. Retain every failure. Never copy development metrics into confirmatory claims.
4. Use seed 20260902, `$fn=24`, a 120-second kernel timeout, and no artifact reuse.

This protocol is exploratory/development evidence only.
