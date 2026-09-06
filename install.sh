#!/bin/sh
set -eu

OWNER="THE-BU1LD"
REPO="NeuroCAD"
REF="${NEUROCAD_REF:-main}"
INSTALL_ROOT="${NEUROCAD_HOME:-$HOME/.local/share/neurocad}"
BIN_DIR="${NEUROCAD_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
case "$REF" in
  v*) ARCHIVE_URL="https://github.com/$OWNER/$REPO/archive/refs/tags/$REF.zip" ;;
  *) ARCHIVE_URL="https://github.com/$OWNER/$REPO/archive/refs/heads/$REF.zip" ;;
esac

say() { printf '%s\n' "$*"; }
fail() { printf 'NeuroCAD install error: %s\n' "$*" >&2; exit 1; }

PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "python3 is required (Python 3.10+)."

"$PYTHON_BIN" - <<'PY' || fail "Python 3.10 or newer is required."
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY

say "Installing NeuroCAD ($REF)"
mkdir -p "$INSTALL_ROOT" "$BIN_DIR"

if [ ! -x "$VENV/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$VENV" || fail "Could not create virtual environment at $VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV/bin/python" -m pip install --upgrade "$ARCHIVE_URL"

[ -x "$VENV/bin/neurocad" ] || fail "Install completed but the neurocad executable was not created."
ln -sf "$VENV/bin/neurocad" "$BIN_DIR/neurocad"

if [ -x "$VENV/bin/text-to-cad" ]; then
  ln -sf "$VENV/bin/text-to-cad" "$BIN_DIR/text-to-cad"
fi

"$BIN_DIR/neurocad" --version
"$BIN_DIR/neurocad" doctor

case ":${PATH:-}:" in
  *":$BIN_DIR:"*) ;;
  *)
    say ""
    say "Add this to your shell profile if neurocad is not on PATH:"
    say "  export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac

say ""
say "NeuroCAD installed successfully."
say "Try: neurocad create 'a 120 x 80 x 4 mm plate with four 4 mm holes' -o design.scad"
