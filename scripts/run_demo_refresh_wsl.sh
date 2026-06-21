#!/usr/bin/env bash
# Rebuild offline demo from committed measured artifacts (C10 demo refresh).
# Optional: pass --live to re-run FIFO climb before rebuild (needs Verilator in WSL).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}"
export PATH="${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"

LIVE=0
FIFO_STEPS=5
for arg in "$@"; do
  case "${arg}" in
    --live) LIVE=1 ;;
    --fifo-steps=*) FIFO_STEPS="${arg#*=}" ;;
  esac
done

if [[ "${LIVE}" -eq 1 ]]; then
  echo "=== Live FIFO improvement cycle (${FIFO_STEPS} steps) ==="
  bash scripts/run_gen_fifo_wsl.sh "${FIFO_STEPS}"
fi

uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

echo "=== Build offline demo bundle ==="
uv run python scripts/build_demo.py

echo "=== C10 demo rehearsal check ==="
uv run python scripts/check_demo_rehearsal.py

echo "=== Demo ready: open demo/index.html and click Play story ==="