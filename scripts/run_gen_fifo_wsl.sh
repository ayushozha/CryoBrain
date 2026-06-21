#!/usr/bin/env bash
# GEN (C9): REAL measured FIFO climb — propose -> generate_fifo_rtl -> sim
# (cocotb+Verilator) -> measured throughput -> score -> shared memory store.
# Emits artifacts/measured_fifo_climb.json from MEASURED runs only (no proxy).
# Linux-only: needs OSS CAD Suite (Verilator). Cannot run on Windows.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OSS_BIN="${HOME}/utils/oss-cad-suite/bin"
export PATH="${OSS_BIN}:${PATH}"

if [[ ! -x "${OSS_BIN}/verilator" ]]; then
  echo "ERROR: OSS CAD Suite (Verilator) required. Run: bash scripts/install_oss_cad_wsl.sh"
  exit 1
fi

cd "${REPO}"
export PATH="${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"
uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

STEPS="${1:-6}"

echo "=== GEN unit wiring (sim boundary monkeypatched) ==="
uv run pytest tests/test_gen_fifo.py -q

echo "=== GEN real measured FIFO gate (wsl-marked integration) ==="
uv run pytest tests/test_gen_fifo.py -m wsl -q

echo "=== GEN REAL measured FIFO climb (${STEPS} steps) ==="
uv run python -m cryobrain.rl.fifo_loop --steps "${STEPS}"

echo "=== GEN climb artifact ==="
uv run python - "${REPO}/artifacts/measured_fifo_climb.json" <<'PY'
import json, sys
data = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert data["reward_source"] == "measured_fifo_throughput", "reward must be measured, not proxy"
assert data["target"] == "stream_arb_fifo"
hist = data["history"]
print(f"accepted measured FIFO steps: {len(hist)}")
for row in hist:
    assert set(row) == {"step", "throughput", "suppression", "rtl_hash"}, row
    print(f"  step {row['step']}: throughput={row['throughput']:.4f} "
          f"suppression={row['suppression']:+.4f} rtl={row['rtl_hash'][:12]}")
if len(hist) >= 2:
    trend = hist[-1]["throughput"] - hist[0]["throughput"]
    print(f"measured throughput trend: {trend:+.4f}")
    assert trend > 0, "GEN gate: measured throughput must improve over steps"
print("=== GEN PASS (real measured FIFO improvement) ===")
PY
