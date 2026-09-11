#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
  echo "NVIDIA_API_KEY is not set" >&2
  exit 1
fi

MODEL="${NVIDIA_MODEL:-nvidia/nemotron-3-ultra-550b-a55b}"
OUTDIR="${NVIDIA_AUDIT_DIR:-.neurocad-audit/nvidia-dsx}"
mkdir -p "$OUTDIR"

command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq is required (brew install jq)" >&2; exit 1; }

# Collect deterministic local evidence first. Model output is advisory only.
python3 -m compileall -q . >"$OUTDIR/compileall.txt" 2>&1 || true
python3 -m pytest -q --tb=short >"$OUTDIR/pytest.txt" 2>&1 || true

{
  echo "NEUROCAD NVIDIA DSX AUDIT"
  echo "UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "MODEL: $MODEL"
  echo
  echo "=== GIT ==="
  git status --short 2>/dev/null || true
  git rev-parse HEAD 2>/dev/null || true
  echo
  echo "=== PYTHON COMPILE ==="
  cat "$OUTDIR/compileall.txt"
  echo
  echo "=== PYTEST ==="
  cat "$OUTDIR/pytest.txt"
} >"$OUTDIR/evidence.txt"

PROMPT=$(cat <<'EOF'
You are the review layer for NeuroCAD, a strict prompt-to-OpenSCAD research system.

Rules:
- Treat the attached evidence as the only verified runtime evidence.
- Never claim a test passed unless the evidence says it passed.
- Distinguish root cause, hypothesis, and verified fact.
- Preserve deterministic parsing and geometry verification as authorities.
- Prefer the smallest safe correction over broad rewrites.
- Do not weaken tests or validation gates.

Return these sections:
1. Executive diagnosis
2. First causal failure
3. Evidence supporting that diagnosis
4. Smallest safe correction
5. Exact tests required before claiming resolution
6. Additional falsification tests
7. DSX-style production concerns: observability, rate limiting, tenant isolation, failure recovery
EOF
)

PAYLOAD=$(jq -n \
  --arg model "$MODEL" \
  --arg system "$PROMPT" \
  --rawfile evidence "$OUTDIR/evidence.txt" \
  '{
    model: $model,
    messages: [
      {role: "system", content: $system},
      {role: "user", content: $evidence}
    ],
    temperature: 0.2,
    max_tokens: 5000,
    stream: false
  }')

curl --fail-with-body -sS \
  https://integrate.api.nvidia.com/v1/chat/completions \
  -H "Authorization: Bearer ${NVIDIA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  >"$OUTDIR/response.json"

jq -r '.choices[0].message.content // .error.message // .' \
  "$OUTDIR/response.json" | tee "$OUTDIR/review.md"

echo
echo "Artifacts written to $OUTDIR"
