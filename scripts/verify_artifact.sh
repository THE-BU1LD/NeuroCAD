#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3.12}
RUN_DIR=${1:-research/runs/NC-RUN-2026-09-03-FULL}
"$PYTHON_BIN" - "$RUN_DIR" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
expected = manifest.get('artifact_sha256')
if not isinstance(expected, dict) or not expected:
    raise SystemExit('manifest has no artifact hash inventory')
for relative, digest in expected.items():
    path = root / relative
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if actual != digest:
        raise SystemExit(f'artifact mismatch: {relative}')
print(f"verified {len(expected)} artifact hashes for {manifest['run_id']}")
PY
