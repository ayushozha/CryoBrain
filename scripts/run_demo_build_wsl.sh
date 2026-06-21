#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}"
export PATH="${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
uv run python scripts/build_demo.py
uv run python scripts/check_demo_rehearsal.py