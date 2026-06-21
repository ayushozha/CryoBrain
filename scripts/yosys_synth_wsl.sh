#!/usr/bin/env bash
# Run Yosys synth_metrics on an RTL file (G5 helper).
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "usage: $0 <path/to/cryo_brain_decoder.sv>"
  exit 1
fi
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RTL_PATH="$1"
export PATH="${HOME}/utils/oss-cad-suite/bin:${PATH}"
cd "${REPO}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
export RTL_PATH
uv run python - <<'PY'
import json
import os
from pathlib import Path

from cryobrain.rtl_grader.synth_metrics import synth_metrics

print(json.dumps(synth_metrics(Path(os.environ["RTL_PATH"])), indent=2))
PY
