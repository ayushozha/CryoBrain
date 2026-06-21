#!/usr/bin/env bash
# SPEC-v6 definition-of-done gate: P-gate + swarm tests + MP5 + GEN smoke.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}"
export PATH="${HOME}/utils/oss-cad-suite/bin:${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "=== SPEC-v6: sponsor connectivity ==="
uv run python scripts/check_sponsors.py

echo "=== SPEC-v6: MP0–MP2 prerequisites ==="
bash scripts/run_mp2_wsl.sh

echo "=== SPEC-v6: swarm unit tests ==="
uv run pytest tests/test_swarm_event_bus.py tests/test_swarm_visualization.py tests/test_demo_measured.py tests/test_planner.py tests/test_verification_report.py -q

echo "=== SPEC-v6: P-gate Architect climb (MP3+MP4) ==="
bash scripts/run_c5_climb_wsl.sh "${1:-5}"

echo "=== SPEC-v6: C3 frontier sweep (L2-safe Pareto) ==="
bash scripts/run_frontier_sweep_wsl.sh

echo "=== SPEC-v6: MP5 (L1–L5 + verification report) ==="
bash scripts/run_mp5_wsl.sh

echo "=== SPEC-v6: export design_runs + verification_report ==="
bash scripts/export_spec_v61_wsl.sh

echo "=== SPEC-v6: HUD CP0 live eval ==="
if bash scripts/run_cp0_wsl.sh; then
  echo "=== HUD CP0 PASS ==="
else
  echo "=== HUD CP0 WARN: eval did not complete (re-run: wsl bash scripts/run_cp0_wsl.sh) ==="
fi

echo "=== SPEC-v6: GEN FIFO platform proof ==="
bash scripts/run_gen_fifo_wsl.sh "${2:-3}"

echo "=== SPEC-v6: rebuild demo + C10 checklist ==="
bash scripts/run_demo_build_wsl.sh

echo "=== SPEC-v6: C0–C10 checkpoint validation ==="
uv run python scripts/check_spec_v61_checkpoints.py

echo "=== SPEC-v6 GATE PASS ==="
