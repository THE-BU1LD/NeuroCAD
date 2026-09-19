# Evidence ledger

| Evidence | Classification | What it supports | Boundary |
|---|---|---|---|
| Maintained tests/static checks | engineering-verified | current implementation behavior | not scientific external validity |
| `NC-DEV-AUDIT-20260908-NATIVE` | development evidence | fresh 30-task/7-kernel end-to-end pipeline | dirty audit tree; small diagnostic suite |
| Prompt challenge v1 | development evidence | 24/24 stored audit-authored accept/reject cases | authored after code inspection; not independent |
| `NC-RUN-2026-09-03-FULL` | development evidence | historical controlled outcomes | source-unbound; 181 kernel artifacts resumed |
| `NC-REPRO-CB1D4A9` | source-bound negative evidence | clean commit, 240/240 fresh kernel checks, and 999/1,000 IR stress programs | exposed and preserves the pre-fix IR/exporter minimum-length mismatch |
| `NC-REPRO-508EC40` | source-bound controlled evidence | clean commit; 240/240 compiler, 1,000/1,000 IR, 240/240 invalid rejection, 200/200 constraints, 200/200 edits, 240/240 fresh kernel | synthetic project-authored grammar; not independent external validity |
| NC-EXP-001 | development evidence | 240/240 generated contract exactness; simple baseline differences | synthetic grammar only |
| NC-EXP-002 | development evidence | 1,000 static IR invariants | generated programs only |
| NC-EXP-003 | development evidence | rejection of eight categories | eight templates repeated; no 240-sample inference |
| NC-EXP-004 | development evidence | declared constraints detect injected drift | not inference or solving |
| NC-EXP-005 | development evidence | automated named edits | not human usability |
| NC-EXP-006 | development evidence | 240 retained mesh checks | historical provenance/reuse limitation |
| NC-EXP-007 | engineering stress | depth 128 accepted, 129 rejected | constructed bound only |
| VeriCodeGen Stage 1 | negative/falsified | scripted plumbing made no model calls | no model effect |
| VeriCodeGen S3 | not yet run | pipeline only | authorization/provider/budget required |
| Physical/public/external validation | not yet run | nothing yet | `EXTERNAL_EXECUTION_REQUIRED` |

Detailed quantitative claim policy remains in `audits/CLAIM_LEDGER.md`.
