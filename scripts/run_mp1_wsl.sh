#!/usr/bin/env bash
# MP1: 3 DesignConfigs → 3 distinct measured (area_um2, candidate_ler).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

if [[ ! -x "${OSS_BIN}/verilator" ]] || [[ ! -x "${OSS_BIN}/yosys" ]]; then
  echo "ERROR: OSS CAD Suite required. Run: bash scripts/install_oss_cad_wsl.sh"
  exit 1
fi

cd "${REPO}"
export PATH="${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

echo "=== MP1 prerequisite: MP0 ==="
bash scripts/run_mp0_wsl.sh

echo "=== MP1 synth + verify layers ==="
uv run pytest tests/test_synth_metrics.py tests/test_l1_functional.py tests/test_l4_synth.py tests/test_l5_budget.py -q

echo "=== MP1 keystone: 3 variants distinct ==="
uv run pytest tests/test_mp1_variants.py -q

echo "=== MP1 PASS ==="