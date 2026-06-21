#!/usr/bin/env bash
# MP0: keystone — worse RTL → worse measured candidate_ler (SPEC-v5 P0).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

if [[ ! -x "${OSS_BIN}/verilator" ]]; then
  echo "ERROR: OSS CAD Suite not installed. Run: bash scripts/install_oss_cad_wsl.sh"
  exit 1
fi

cd "${REPO}"
echo "=== MP0 tool versions ==="
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

echo "=== MP0 unit tests (no EDA) ==="
uv run pytest tests/test_measured_ler_types.py tests/test_stim_manifest.py tests/test_design_config.py tests/test_rtl_generator.py -q

echo "=== MP0 keystone (Verilator + Stim) ==="
uv run pytest tests/test_measured_ler.py tests/test_keystone_rule.py -q

echo "=== MP0 PASS ==="