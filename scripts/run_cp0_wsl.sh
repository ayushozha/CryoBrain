#!/usr/bin/env bash
# CP0: real tooling + real hud eval (no simulations).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

if [[ ! -x "${OSS_BIN}/verilator" ]]; then
  echo "ERROR: OSS CAD Suite not installed. Run: bash scripts/install_oss_cad_wsl.sh"
  exit 1
fi

cd "${REPO}"
echo "=== CP0 tool versions ==="
verilator --version | head -1
yosys -V | head -1
sby --version | head -1
z3 -version | head -1

export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

# Linux venv (Windows .venv is not usable from WSL).
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
if [[ -z "${HUD_API_KEY:-}" ]]; then
  echo "ERROR: HUD_API_KEY not set (add to ${REPO}/.env)"
  exit 1
fi

echo "=== CP0 hud eval (stream-arb-fifo-cocotb-dv) ==="
hud eval tasks.py claude --task-ids stream-arb-fifo-cocotb-dv --group 1 -y