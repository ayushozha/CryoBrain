#!/usr/bin/env bash
# C3 — launch the Modal parallel measurement fan-out (SPEC-v5 MP3).
#
# Real fan-out runs on Modal (Linux containers with verilator+yosys+stim).
# Modal + EDA are NOT available on Windows: there, use --dry-run, which
# validates wiring/shape locally with ONE variant and never calls Modal.
#
# Usage:
#   scripts/launch_modal_measure.sh --dry-run            # local wiring/shape check
#   scripts/launch_modal_measure.sh --dry-run --rtl X.sv # dry-run a specific RTL
#   scripts/launch_modal_measure.sh --rtl a.sv --rtl b.sv  # real fan-out (needs Modal)
#
# When MODAL_TOKEN_ID / MODAL_TOKEN_SECRET are set and `modal` is installed,
# the non-dry-run path fans out one container per RTL via `modal run`.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}"

# Prefer uv if present (matches the rest of scripts/), else fall back to python.
RUN_PY=(python)
if command -v uv >/dev/null 2>&1; then
  RUN_PY=(uv run python)
fi

DRY_RUN=0
for arg in "$@"; do
  if [[ "${arg}" == "--dry-run" ]]; then
    DRY_RUN=1
  fi
done

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "=== C3 dry-run (no Modal call): validate fan-out wiring/shape ==="
  PYTHONPATH="${REPO}" "${RUN_PY[@]}" -m cryobrain.rl.modal_measure "$@"
  echo "=== C3 dry-run done ==="
  exit 0
fi

# Real fan-out. If `modal` CLI is installed, prefer `modal run` so the launch is
# the canonical Modal entrypoint; otherwise drive the Python module (which still
# dispatches to Modal .map when tokens are present, else local fallback).
if command -v modal >/dev/null 2>&1; then
  echo "=== C3 Modal fan-out via 'modal run' ==="
  modal run cryobrain/rl/modal_measure.py "$@"
else
  echo "=== C3 fan-out via python module (modal CLI not found) ==="
  PYTHONPATH="${REPO}" "${RUN_PY[@]}" -m cryobrain.rl.modal_measure "$@"
fi
