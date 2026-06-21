#!/usr/bin/env bash
# Run the Verilator-backed RTL flow for a staged CryoBrain workdir.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <workdir-with-rtl-dv-synth>"
  exit 1
fi

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORKDIR="$1"
export PATH="${HOME}/utils/oss-cad-suite/bin:${PATH}"

cd "${REPO}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
export WORKDIR

uv run python - <<'PY'
import json
import os
from pathlib import Path

from cryobrain.rtl_grader.flow import run_rtl_flow

result = run_rtl_flow(Path(os.environ["WORKDIR"]))
print(json.dumps({**result.__dict__, "rtl_valid": result.rtl_valid}, indent=2))
raise SystemExit(0 if result.rtl_valid else 1)
PY
