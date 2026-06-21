#!/usr/bin/env bash
# SPEC-v6 P-train2: REAL planner measured climb — Planner -> Architect ->
# generate_rtl -> verify (L1/L4/L5) -> measure_candidate_ler -> score_measured.
# Emits artifacts/planner_climb.json (measured_climb schema + planner_source tag).
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

echo "=== Planner prerequisite: C5 Architect climb gate (MP3) ==="
bash scripts/run_c5_climb_wsl.sh 1

echo "=== Planner unit wiring (boundary monkeypatched) ==="
uv run pytest tests/test_planner.py -q

echo "=== Planner REAL measured climb (${STEPS} steps, deterministic planner) ==="
uv run python -m cryobrain.rl.planner_trainer --steps "${STEPS}"

echo "=== Planner climb artifact ==="
uv run python - "${REPO}/artifacts/planner_climb.json" <<'PY'
import json, sys
data = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert data["reward_source"] == "score_measured", "reward must be measured, not proxy"
assert data.get("planner_source") == "cryobrain.swarm.planner", "planner_source tag required"
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

echo "=== Planner PASS (real P-train2 measured climb) ==="
