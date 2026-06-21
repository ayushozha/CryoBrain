#!/usr/bin/env bash
# MP5: run the full L1-L5 gate once later milestone tests have landed.
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

echo "=== MP5 prerequisite: MP0 ==="
bash scripts/run_mp0_wsl.sh

echo "=== MP5 prerequisite: MP1 ==="
bash scripts/run_mp1_wsl.sh

tests=(
  tests/test_l1_functional.py
  tests/test_l4_synth.py
  tests/test_l5_budget.py
  tests/test_l3_formal.py
  tests/test_verification_report.py
)

present=()
missing=()
for test_path in "${tests[@]}"; do
  if [[ -f "$test_path" ]]; then
    present+=("$test_path")
  else
    missing+=("$test_path")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  printf 'MP5 blocker: missing tests:\n'
  printf '  %s\n' "${missing[@]}"
  exit 2
fi

uv run pytest "${present[@]}" -q
echo "=== MP5 PASS ==="
