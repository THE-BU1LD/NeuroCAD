#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${NEUROCAD_REPO_URL:-https://github.com/THE-BU1LD/NeuroCAD.git}"
REF="${NEUROCAD_REF:-main}"
INSTALLER_URL="${NEUROCAD_INSTALLER_URL:-https://raw.githubusercontent.com/THE-BU1LD/NeuroCAD/${REF}/install.sh}"
EVIDENCE_PATH="${NEUROCAD_EVIDENCE_PATH:-public-alpha-evidence.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/neurocad-public-alpha.XXXXXX")"
CLEAN_HOME="$WORKDIR/home"
INSTALL_ROOT="$CLEAN_HOME/.local/share/neurocad"
BIN_DIR="$CLEAN_HOME/.local/bin"
INSTALLER_PATH="$WORKDIR/install.sh"
SMOKE_OUTPUT="$WORKDIR/smoke.scad"
STARTED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RESOLVED_COMMIT=""
RESOLVED_COMMIT_AFTER=""
EXPECTED_COMMIT="${NEUROCAD_EXPECTED_COMMIT:-}"
INSTALLED_VERSION=""
SMOKE_SHA256=""

mkdir -p "$CLEAN_HOME" "$(dirname "$EVIDENCE_PATH")"

write_evidence() {
  local exit_code="$1"
  "$PYTHON_BIN" - "$EVIDENCE_PATH" "$exit_code" "$STARTED_AT_UTC" "$REPO_URL" "$REF" \
    "$INSTALLER_URL" "$EXPECTED_COMMIT" "$RESOLVED_COMMIT" "$RESOLVED_COMMIT_AFTER" \
    "$INSTALLED_VERSION" "$SMOKE_SHA256" "$CLEAN_HOME" <<'PY'
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    evidence_path,
    exit_code,
    started_at,
    repo_url,
    ref,
    installer_url,
    expected_commit,
    resolved_before,
    resolved_after,
    installed_version,
    smoke_sha256,
    clean_home,
) = sys.argv[1:]

payload = {
    "schema_version": 1,
    "verification": "neurocad-public-alpha-clean-room",
    "started_at_utc": started_at,
    "finished_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "exit_status": int(exit_code),
    "repository_url": repo_url,
    "ref": ref,
    "installer_url": installer_url,
    "expected_commit": expected_commit or None,
    "resolved_commit_before_install": resolved_before or None,
    "resolved_commit_after_install": resolved_after or None,
    "installed_version": installed_version or None,
    "python_version": platform.python_version(),
    "platform": platform.platform(),
    "isolated_home": clean_home,
    "credential_isolation": {
        "temporary_home": True,
        "github_token_environment_unset": True,
        "git_askpass_unset": True,
        "ssh_auth_sock_unset": True,
    },
    "smoke": {
        "command": "neurocad create 'a compact box with two holes' -o <temp>/smoke.scad",
        "output_sha256": smoke_sha256 or None,
    },
}
Path(evidence_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

cleanup() {
  local exit_code=$?
  set +e
  write_evidence "$exit_code"
  rm -rf "$WORKDIR"
  exit "$exit_code"
}
trap cleanup EXIT

# Run with a fresh HOME and without ambient GitHub/SSH credential channels.
unset GH_TOKEN GITHUB_TOKEN GIT_ASKPASS SSH_AUTH_SOCK GIT_SSH_COMMAND || true
export HOME="$CLEAN_HOME"
export PATH="$BIN_DIR:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

RESOLVED_COMMIT="$(git ls-remote "$REPO_URL" "refs/heads/$REF" | awk 'NR == 1 {print $1}')"
[[ "$RESOLVED_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
  echo "Could not resolve public branch '$REF' without credentials." >&2
  exit 1
}

if [[ -z "$EXPECTED_COMMIT" ]]; then
  EXPECTED_COMMIT="$RESOLVED_COMMIT"
fi

if [[ "$RESOLVED_COMMIT" != "$EXPECTED_COMMIT" ]]; then
  echo "Resolved commit $RESOLVED_COMMIT does not match expected $EXPECTED_COMMIT." >&2
  exit 1
fi

curl -fsSL "$INSTALLER_URL" -o "$INSTALLER_PATH"

HOME="$CLEAN_HOME" \
NEUROCAD_HOME="$INSTALL_ROOT" \
NEUROCAD_BIN_DIR="$BIN_DIR" \
NEUROCAD_REF="$REF" \
PYTHON_BIN="$PYTHON_BIN" \
  sh "$INSTALLER_PATH"

[[ -x "$BIN_DIR/neurocad" ]] || {
  echo "Installed neurocad executable is missing." >&2
  exit 1
}

INSTALLED_VERSION="$($BIN_DIR/neurocad --version)"
"$BIN_DIR/neurocad" doctor
"$BIN_DIR/neurocad" create "a compact box with two holes" -o "$SMOKE_OUTPUT"
[[ -s "$SMOKE_OUTPUT" ]] || {
  echo "Installed CLI smoke output is missing or empty." >&2
  exit 1
}

SMOKE_SHA256="$($PYTHON_BIN - "$SMOKE_OUTPUT" <<'PY'
import hashlib
import sys
from pathlib import Path
p = Path(sys.argv[1])
print(hashlib.sha256(p.read_bytes()).hexdigest())
PY
)"

# Fail if the public branch moved while the installer was running; this keeps the receipt exact-head.
RESOLVED_COMMIT_AFTER="$(git ls-remote "$REPO_URL" "refs/heads/$REF" | awk 'NR == 1 {print $1}')"
if [[ "$RESOLVED_COMMIT_AFTER" != "$EXPECTED_COMMIT" ]]; then
  echo "Public branch moved during verification: expected $EXPECTED_COMMIT, now $RESOLVED_COMMIT_AFTER." >&2
  exit 1
fi

printf 'Clean-room public-alpha verification passed for %s@%s\n' "$REF" "$EXPECTED_COMMIT"
printf 'Evidence: %s\n' "$EVIDENCE_PATH"
