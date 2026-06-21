#!/usr/bin/env bash
# Run Yosys synth_metrics on an RTL file (G5 helper).
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "usage: $0 <path/to/cryo_brain_decoder.sv>"
  exit 1
fi
REPO="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/utils/oss-cad-suite/bin:${PATH}"
cd "${REPO}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
uv run python -c "from pathlib import Path; from cryobrain.rtl_grader.synth_metrics import synth_metrics; import json; print(json.dumps(synth_metrics(Path('$1')), indent=2))"