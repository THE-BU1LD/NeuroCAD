# Statistical analysis plan

Outcomes and comparison rules were fixed in `QUESTION.md`. The unit of analysis for NC-EXP-001 is a task. Semantic exactness requires every declared expected field to match within 1e-6 for numeric values. Failed parsing is incorrect. No task is dropped.

For each finite-binomial engineering rate, report numerator, denominator, point estimate, and two-sided 95% Wilson interval. Compare NeuroCAD with each baseline on the same tasks using an exact two-sided McNemar test; report both discordant cell counts and the p-value. This test is descriptive because tasks come from a controlled generator, not a random sample of natural requests. No multiple-testing-adjusted discovery claim is made.

Latency is local wall-clock diagnostic data. Report mean and p95 for IR evaluation and mean for automated edit operations. Do not compare cross-system latency as a hardware-independent result. Peak memory uses Python `tracemalloc` and excludes native library allocations.

Training randomness and multi-seed model analysis are not applicable: NeuroCAD and all baselines are deterministic. The seed controls data generation only. If a learned model is later introduced, it requires at least three training seeds, predeclared selection, mean/dispersion across seeds, compute and parameter accounting, and a new analysis plan.

