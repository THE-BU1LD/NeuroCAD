#!/bin/sh
set -eu

REPO_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$REPO_DIR"

PYTHON_BIN=${PYTHON_BIN:-python3.12}
EXPECTED_PYTHON_VERSION=3.12.14
ACTUAL_PYTHON_VERSION=$(
    "$PYTHON_BIN" -c 'import platform; print(platform.python_version())'
)
if [ "$ACTUAL_PYTHON_VERSION" != "$EXPECTED_PYTHON_VERSION" ]; then
    printf '%s\n' \
        "Research reproduction requires Python $EXPECTED_PYTHON_VERSION; got $ACTUAL_PYTHON_VERSION from $PYTHON_BIN." >&2
    exit 2
fi

if ! command -v openscad >/dev/null 2>&1; then
    printf '%s\n' "OpenSCAD is required for the kernel-backed research run." >&2
    exit 2
fi

# Linux OpenSCAD builds may require an X server even for PNG output. Re-enter
# once through Xvfb when it is installed and no display is already available.
# macOS OpenSCAD uses NSOpenGLContext, so forcing Qt's offscreen backend there
# is actively harmful and is intentionally avoided.
KERNEL_OS=$(uname -s)
if [ "$KERNEL_OS" = "Linux" ] && [ -z "${DISPLAY:-}" ]; then
    if command -v xvfb-run >/dev/null 2>&1 && [ "${NEUROCAD_XVFB_ACTIVE:-0}" != "1" ]; then
        NEUROCAD_XVFB_ACTIVE=1
        export NEUROCAD_XVFB_ACTIVE
        exec xvfb-run -a "$0" "$@"
    fi
    QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-offscreen}
    export QT_QPA_PLATFORM
fi

REPRO_WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/neurocad-repro.XXXXXX")
cleanup() {
    rm -rf -- "$REPRO_WORK_DIR"
}
trap cleanup EXIT INT TERM

REPRO_ENV="$REPRO_WORK_DIR/venv"
DIST_DIR="$REPRO_WORK_DIR/dist"
RUN_STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
RUN_PARENT=${NEUROCAD_RESEARCH_RUN_PARENT:-research/runs}

if [ -n "${NEUROCAD_RESEARCH_RUN_DIR:-}" ]; then
    RUN_DIR=$NEUROCAD_RESEARCH_RUN_DIR
    if [ -e "$RUN_DIR" ]; then
        printf '%s\n' "Research output must not already exist: $RUN_DIR" >&2
        exit 2
    fi
    mkdir -p -- "$(dirname -- "$RUN_DIR")"
    mkdir -- "$RUN_DIR"
else
    mkdir -p -- "$RUN_PARENT"
    RUN_DIR=$(mktemp -d "$RUN_PARENT/NC-REPRO-$RUN_STAMP.XXXXXX")
fi
RUN_DIR=$(CDPATH='' cd -- "$RUN_DIR" && pwd)
CANONICAL_FROZEN_DIR="$REPO_DIR/research/runs/NC-RUN-2026-09-03-FULL"
if [ "$RUN_DIR" = "$CANONICAL_FROZEN_DIR" ]; then
    printf '%s\n' "Refusing to overwrite the canonical frozen research run." >&2
    exit 2
fi
RUN_ID=${NEUROCAD_RESEARCH_RUN_ID:-NC-REPRO-$RUN_STAMP}

"$PYTHON_BIN" -m venv "$REPRO_ENV"
"$REPRO_ENV/bin/python" -m pip install \
    --require-hashes \
    --requirement requirements-research.lock
"$REPRO_ENV/bin/python" -m pip install --no-build-isolation --no-deps -e .

# Fail before the expensive suite if the native kernel exists but cannot create
# a mesh-rendering context on this host.
PYTHON_BIN="$REPRO_ENV/bin/python" scripts/preflight.sh

"$REPRO_ENV/bin/python" -m compileall -q \
    neurocad_cli.py text_to_cad.py text_to_openscad.py core research/vericodegen
"$REPRO_ENV/bin/python" -m pytest -q tests
"$REPRO_ENV/bin/python" -m ruff check \
    core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py tests
"$REPRO_ENV/bin/python" -m mypy \
    core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py
"$REPRO_ENV/bin/python" -m pip check
"$REPRO_ENV/bin/python" -m pip_audit \
    --requirement requirements-research.lock \
    --no-deps \
    --disable-pip \
    --progress-spinner off
"$REPRO_ENV/bin/python" -m bandit -q -r \
    core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py \
    -x '*/__pycache__/*'

# Construct the research configuration here so forced recompilation is an
# explicit reproduction input rather than an implicit CLI default.
"$REPRO_ENV/bin/python" - "$RUN_DIR" "$RUN_ID" <<'PY'
import sys
from pathlib import Path

from core.research_suite import ResearchConfig, run_research_suite

config = ResearchConfig(
    compiler_tasks=240,
    ir_programs=1000,
    invalid_cases=240,
    edit_cases=200,
    constraint_ablation_cases=200,
    kernel_samples=240,
    fn=48,
    force_recompile=True,
)
run_research_suite(
    Path(sys.argv[1]),
    config,
    require_kernel=True,
    run_id=sys.argv[2],
)
PY

"$REPRO_ENV/bin/python" - "$RUN_DIR" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
results = json.loads((run_dir / "metrics" / "results.json").read_text(encoding="utf-8"))
kernel = results["experiments"]["NC-EXP-006"]
assert config["force_recompile"] is True
assert manifest["force_recompile"] is True
assert manifest["artifact_reuse_allowed"] is False
assert kernel["resumed_verified_samples"] == 0
assert manifest["provenance"]["source"]["sha256"]
assert manifest["provenance"]["requirements_lock"]["sha256"]
assert manifest["provenance"]["openscad"]["version_output"]
assert manifest["provenance"]["openscad"]["executable_sha256"]
assert (run_dir / manifest["deterministic_results"]).is_file()
assert (run_dir / manifest["runtime_receipt"]).is_file()
PY

mkdir -p -- "$DIST_DIR"
"$REPRO_ENV/bin/python" -m build --no-isolation --outdir "$DIST_DIR"

set -- "$DIST_DIR"/neurocad_research-*.whl
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
    printf '%s\n' "Expected exactly one freshly built wheel in $DIST_DIR." >&2
    exit 2
fi
WHEEL_PATH=$1

VERIFY_ENV="$REPRO_WORK_DIR/wheel-verify"
"$PYTHON_BIN" -m venv "$VERIFY_ENV"
"$VERIFY_ENV/bin/python" -m pip install \
    --require-hashes \
    --requirement requirements-research.lock
"$VERIFY_ENV/bin/python" -m pip install --no-deps "$WHEEL_PATH"
"$VERIFY_ENV/bin/neurocad" doctor
"$VERIFY_ENV/bin/neurocad" create \
    "a 40 x 30 x 3 mm plate with four 3 mm holes" \
    -o "$REPRO_WORK_DIR/fresh-wheel.scad"
test -s "$REPRO_WORK_DIR/fresh-wheel.scad"

printf '%s\n' "Research run completed at $RUN_DIR"
printf '%s\n' "The disposable build environment and distributions were removed after verification."
