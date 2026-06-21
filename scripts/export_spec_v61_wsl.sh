#!/usr/bin/env bash
# Export SPEC-v6.1 design_runs + verification_report from measured golden (WSL).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"

cd "${REPO}"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

uv run python scripts/export_spec_v61_artifacts.py --design-runs 3
echo "=== SPEC-v6.1 artifact export PASS ==="