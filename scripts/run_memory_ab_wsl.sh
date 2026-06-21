#!/usr/bin/env bash
# SPEC2 CP5: memory-on vs memory-off overlay in WSL with OSS CAD.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

cd "${REPO}"
export PATH="${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync --extra rl --extra sponsors
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

python scripts/run_memory_ab.py "$@"
