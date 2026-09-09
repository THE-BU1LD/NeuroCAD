#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3.12}
RUN_DIR=${1:-research/runs/NC-RUN-2026-09-03-FULL}
"$PYTHON_BIN" - "$RUN_DIR" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]) / 'metrics' / 'results.json'
d = json.loads(p.read_text(encoding='utf-8'))
e = d['experiments']
c = e['NC-EXP-001']['systems']
print(f"run_id={d['run_id']}")
for name in ('neurocad','normalized_dimensions_only','nearest_neighbor_retrieval','raw_numbers_no_unit_normalization','fixed_box'):
    if name not in c:
        continue
    print(f"{name}={c[name]['overall_semantic_exact_rate']:.6f}")
for exp in ('NC-EXP-002','NC-EXP-003','NC-EXP-004','NC-EXP-005','NC-EXP-006','NC-EXP-007'):
    print(exp, json.dumps({k:v for k,v in e[exp].items() if k not in {'records','rows'}}, sort_keys=True))
PY
