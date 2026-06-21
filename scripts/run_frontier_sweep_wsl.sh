#!/usr/bin/env bash
# C3: measure all L2-safe variants and populate memory store for Pareto frontier.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${HOME}/.local/bin:${PATH}"

cd "${REPO}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync --extra rl --extra sponsors
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
PYTHON="${UV_PROJECT_ENVIRONMENT}/bin/python"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "=== C3 frontier sweep (L2-safe variants -> memory store) ==="
"${PYTHON}" -m cryobrain.benchmark.frontier_sweep

echo "=== C3 measured Pareto ==="
"${PYTHON}" -m cryobrain.benchmark.pareto --emit "${REPO}/artifacts/measured_pareto.json"

"${PYTHON}" - "${REPO}/artifacts/measured_pareto.json" <<'PY'
import json, sys
data = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert data["count"] >= 2, f"C3 needs 2+ measured points, got {data['count']}"
print(f"C3 PASS: {data['count']} measured pareto points")
PY
