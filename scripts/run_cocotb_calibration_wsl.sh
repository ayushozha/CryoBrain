#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/utils/oss-cad-suite/bin:${REPO}/.venv-linux/bin:${HOME}/.local/bin:${PATH}"
cd "${REPO}"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
python tasks/stream_arb_fifo_cocotb_dv/scripts/check_calibration.py
