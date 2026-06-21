#!/usr/bin/env bash
# MP3 (C5): REAL measured climb — propose -> generate_rtl -> verify (L1/L4/L5)
# -> measure_candidate_ler (Stim->Verilator) -> score_measured (Yosys) -> memory.
# Emits artifacts/measured_climb.json from MEASURED runs only (no proxy).
# Linux-only: needs OSS CAD Suite (Verilator + Yosys). Cannot run on Windows.
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

STEPS="${1:-5}"

echo "=== C5 prerequisite: MP2 (measured reward) ==="
bash scripts/run_mp2_wsl.sh

echo "=== C5 unit wiring (boundary monkeypatched) ==="
uv run pytest tests/test_local_trainer_measured.py -q

PROPOSER_ARGS=(--no-fireworks)
if [[ -n "${FIREWORKS_API_KEY:-}" ]]; then
  echo "=== C5 sponsor: Fireworks Architect proposer enabled ==="
  PROPOSER_ARGS=(--fireworks)
else
  echo "=== C5 measured climb (${STEPS} steps, deterministic proposer; set FIREWORKS_API_KEY for sponsor path) ==="
fi
uv run python -m cryobrain.rl.local_trainer --steps "${STEPS}" "${PROPOSER_ARGS[@]}" --memory-ab

echo "=== C5 measured Pareto ==="
uv run python -m cryobrain.benchmark.pareto --emit "${REPO}/artifacts/measured_pareto.json"

echo "=== C5 climb artifact ==="
uv run python - "${REPO}/artifacts/measured_climb.json" <<'PY'
import json, sys
data = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert data["reward_source"] == "score_measured", "reward must be measured, not proxy"
hist = data["history"]
print(f"accepted measured steps: {len(hist)}")
for row in hist:
    assert set(row) == {"step", "candidate_ler", "suppression", "rtl_hash"}, row
    print(f"  step {row['step']}: ler={row['candidate_ler']:.4f} "
          f"suppression={row['suppression']:+.4f} rtl={row['rtl_hash'][:12]}")
if len(hist) >= 2:
    trend = hist[-1]["suppression"] - hist[0]["suppression"]
    print(f"measured suppression trend: {trend:+.4f}")
PY

echo "=== C5 PASS (real MP3 measured climb) ==="
