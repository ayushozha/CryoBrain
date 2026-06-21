#!/usr/bin/env bash
# Multi-hour measured improvement marathon: agents keep climbing and emitting artifacts.
# Usage: bash scripts/run_improvement_marathon_wsl.sh [cycles] [steps_per_agent] [pause_secs] [min_iterations]
# Example: bash scripts/run_improvement_marathon_wsl.sh 50 2 0 50
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${HOME}/.local/bin:${PATH}"

if [[ ! -x "${OSS_BIN}/verilator" ]] || [[ ! -x "${OSS_BIN}/yosys" ]]; then
  echo "ERROR: OSS CAD Suite required. Run: bash scripts/install_oss_cad_wsl.sh"
  exit 1
fi

cd "${REPO}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync --extra rl --extra sponsors
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
PYTHON="${UV_PROJECT_ENVIRONMENT}/bin/python"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${MODAL_TOKEN_ID:-}" || -z "${MODAL_TOKEN_SECRET:-}" ]]; then
  MODAL_TOML="${MODAL_TOML:-${HOME}/.modal.toml}"
  if [[ -f "${MODAL_TOML}" ]]; then
    eval "$(python3 - "${MODAL_TOML}" <<'PY'
import shlex
import sys
import tomllib
from pathlib import Path

data = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
profiles = [(name, value) for name, value in data.items() if isinstance(value, dict)]
active = [value for _, value in profiles if value.get("active")]
profile = active[0] if active else (profiles[0][1] if profiles else {})
token_id = str(profile.get("token_id", "")).strip()
token_secret = str(profile.get("token_secret", "")).strip()
if token_id and token_secret:
    print(f"export MODAL_TOKEN_ID={shlex.quote(token_id)}")
    print(f"export MODAL_TOKEN_SECRET={shlex.quote(token_secret)}")
PY
)"
  fi
fi

CYCLES="${1:-6}"
STEPS="${2:-10}"
PAUSE_SECS="${3:-0}"
MIN_ITERATIONS="${4:-${CYCLES}}"
echo "=== Marathon: required sponsor connectivity ==="
"${PYTHON}" scripts/check_sponsors.py --require-core

echo "=== Improvement marathon: ${CYCLES} cycles x ${STEPS} steps, ${PAUSE_SECS}s pause, min ${MIN_ITERATIONS} archived iterations ==="
echo "=== Log: artifacts/improvement_marathon.jsonl ==="

"${PYTHON}" scripts/run_improvement_marathon.py \
  --cycles "${CYCLES}" \
  --steps "${STEPS}" \
  --pause-secs "${PAUSE_SECS}" \
  --min-iterations "${MIN_ITERATIONS}" \
  --require-sponsors

echo "=== Marathon artifacts ==="
ls -la artifacts/measured_climb.json artifacts/measured_fifo_climb.json artifacts/improvement_marathon.jsonl artifacts/measured_50_iteration_summary.json 2>/dev/null || true
