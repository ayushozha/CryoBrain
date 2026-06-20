#!/usr/bin/env bash
# CP4: real graded reward training loop (no synthetic local stub).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

if [[ ! -x "${OSS_BIN}/verilator" ]]; then
  echo "ERROR: OSS CAD Suite not installed. Run: bash scripts/install_oss_cad_wsl.sh"
  exit 1
fi

cd "${REPO}"
echo "=== CP4 tool versions ==="
verilator --version | head -1
yosys -V | head -1

export PATH="${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

echo "=== CP4 real graded training ==="
python scripts/run_rl.py --local "$@"
