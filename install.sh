#!/bin/sh
set -eu

OWNER="THE-BU1LD"
REPO="NeuroCAD"
REF="${NEUROCAD_REF:-v0.5.0a6}"
INSTALL_ROOT="${NEUROCAD_HOME:-$HOME/.local/share/neurocad}"
BIN_DIR="${NEUROCAD_BIN_DIR:-$HOME/.local/bin}"
case "$REF" in
  v*) ARCHIVE_URL="https://github.com/$OWNER/$REPO/archive/refs/tags/$REF.zip" ;;
  *) ARCHIVE_URL="https://github.com/$OWNER/$REPO/archive/refs/heads/$REF.zip" ;;
esac
PACKAGE="${NEUROCAD_PACKAGE:-$ARCHIVE_URL}"

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
INSTALL_ROOT=$(CDPATH= cd -- "$INSTALL_ROOT" && pwd -P)
BIN_DIR=$(CDPATH= cd -- "$BIN_DIR" && pwd -P)
LOCK="$INSTALL_ROOT/.install-lock"
mkdir "$LOCK" 2>/dev/null || fail "Another install is active ($LOCK); inspect before removing a stale lock."
VENV=""
PUBLISHED=0
cleanup() {
  # VENV is exclusively a new mktemp directory, never a user-supplied target.
  if [ "$PUBLISHED" -eq 0 ] && [ -n "$VENV" ]; then rm -rf -- "$VENV"; fi
  rmdir "$LOCK" 2>/dev/null || true
}
trap cleanup 0
trap 'exit 130' 1 2 15

check_launcher() {
  launcher="$BIN_DIR/$1"
  if [ -L "$launcher" ]; then
    target=$(readlink "$launcher")
    case "$target" in
      "$INSTALL_ROOT"/releases/*/bin/"$1"|"$INSTALL_ROOT"/venv/bin/"$1") ;;
      *) fail "Refusing to replace an unrelated launcher: $launcher" ;;
    esac
  elif [ -e "$launcher" ]; then
    fail "Refusing to replace an existing file or directory: $launcher"
  fi
}
check_launcher neurocad
check_launcher text-to-cad
mkdir -p "$INSTALL_ROOT/releases"
VENV=$(mktemp -d "$INSTALL_ROOT/releases/install.XXXXXX")
"$PYTHON_BIN" -m venv "$VENV" || fail "Could not create virtual environment at $VENV"
"$VENV/bin/python" -m pip install --upgrade "pip==26.2.1" >/dev/null
"$VENV/bin/python" -m pip install "$PACKAGE" ||
  fail "Package unavailable or invalid. Private GitHub refs need access; from a checkout use NEUROCAD_PACKAGE=\"\$PWD\" sh ./install.sh."
"$VENV/bin/python" -m pip check
[ -x "$VENV/bin/neurocad" ] || fail "Install completed but the neurocad executable was not created."
[ -x "$VENV/bin/text-to-cad" ] || fail "Install completed but the text-to-cad executable was not created."
installed_version=$("$VENV/bin/neurocad" --version)
case "$REF" in
  v*)
    expected_version=${REF#v}
    [ "$installed_version" = "NeuroCAD $expected_version" ] ||
      fail "Installed version does not match $REF: $installed_version"
    ;;
esac
say "$installed_version"
"$VENV/bin/neurocad" doctor || fail "The staged installation failed its health check; existing launchers are unchanged."
"$VENV/bin/neurocad" validate "a 120 x 80 x 4 mm plate with four 4 mm holes" >/dev/null
publish_launcher() {
  check_launcher "$1"
  ln -s "$VENV/bin/$1" "$LOCK/$1"
  # Keep the staged environment if publication partially succeeds; a launcher
  # must never point at a directory removed by failure cleanup.
  PUBLISHED=1
  mv -f "$LOCK/$1" "$BIN_DIR/$1"
}
publish_launcher neurocad
publish_launcher text-to-cad
say "Previous environments are retained in $INSTALL_ROOT for rollback."

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
