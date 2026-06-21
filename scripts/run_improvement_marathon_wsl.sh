#!/usr/bin/env bash
# Multi-hour measured improvement marathon: agents keep climbing and emitting artifacts.
# Usage: bash scripts/run_improvement_marathon_wsl.sh [cycles] [steps_per_agent]
# Example: bash scripts/run_improvement_marathon_wsl.sh 8 10
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
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

CYCLES="${1:-6}"
STEPS="${2:-10}"
FIREWORKS_FLAG=()
if [[ -n "${FIREWORKS_API_KEY:-}" ]]; then
  FIREWORKS_FLAG=(--fireworks)
  echo "=== Marathon: Fireworks proposer enabled ==="
fi

echo "=== Improvement marathon: ${CYCLES} cycles x ${STEPS} steps ==="
echo "=== Log: artifacts/improvement_marathon.jsonl ==="

uv run python scripts/run_improvement_marathon.py \
  --cycles "${CYCLES}" \
  --steps "${STEPS}" \
  --pause-secs 15 \
  "${FIREWORKS_FLAG[@]}"

echo "=== Marathon artifacts ==="
ls -la artifacts/measured_climb.json artifacts/measured_fifo_climb.json artifacts/improvement_marathon.jsonl 2>/dev/null || true