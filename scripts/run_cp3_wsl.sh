#!/usr/bin/env bash
# CP3: real multi-rollout reward calibration (no simulations).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

if [[ ! -x "${OSS_BIN}/verilator" ]]; then
  echo "ERROR: OSS CAD Suite not installed. Run: bash scripts/install_oss_cad_wsl.sh"
  exit 1
fi

cd "${REPO}"
echo "=== CP3 tool versions ==="
verilator --version | head -1
yosys -V | head -1

export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

echo "=== CP3 calibration (10 rollouts) ==="
python tasks/cryo_brain_decoder/scripts/check_calibration.py
