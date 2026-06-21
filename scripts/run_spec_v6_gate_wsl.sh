#!/usr/bin/env bash
# SPEC-v6 definition-of-done gate: P-gate + swarm tests + MP5 + GEN smoke.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}"
export PATH="${HOME}/utils/oss-cad-suite/bin:${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

echo "=== SPEC-v6: MP0–MP2 prerequisites ==="
bash scripts/run_mp2_wsl.sh

echo "=== SPEC-v6: swarm unit tests ==="
uv run pytest tests/test_swarm_event_bus.py tests/test_swarm_visualization.py tests/test_demo_measured.py tests/test_planner.py tests/test_verification_report.py -q

echo "=== SPEC-v6: P-gate Architect climb (MP3+MP4) ==="
bash scripts/run_c5_climb_wsl.sh "${1:-3}"

echo "=== SPEC-v6: MP5 (L1–L5 + verification report) ==="
bash scripts/run_mp5_wsl.sh

echo "=== SPEC-v6: GEN FIFO platform proof ==="
bash scripts/run_gen_fifo_wsl.sh "${2:-3}"

echo "=== SPEC-v6: rebuild demo from measured artifacts ==="
uv run python scripts/build_demo.py

echo "=== SPEC-v6 GATE PASS ==="
