#!/usr/bin/env bash
# MP2: reward moves only on measured change; grade path uses score_measured.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

cd "${REPO}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
export PATH="${HOME}/.local/bin:${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
uv sync

echo "=== MP2 prerequisite: MP1 ==="
bash scripts/run_mp1_wsl.sh

echo "=== MP2 proxy guard ==="
uv run pytest tests/test_no_proxy_ler_in_prod.py tests/test_proxy_removed.py -q

echo "=== MP2 score_measured ==="
uv run pytest tests/test_score_measured.py -q

echo "=== MP2 PASS ==="
