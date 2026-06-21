#!/usr/bin/env bash
# X9: compute real MWPM/Stim LER baselines from the checked Stim manifest.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}"

export PATH="${HOME}/.local/bin:${PATH}"
export UV_PROJECT_ENVIRONMENT="${REPO}/.venv-linux"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required in WSL. Install uv, then rerun this script."
  exit 1
fi

uv sync
export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

uv run python - <<'PY'
from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pymatching
import stim

from cryobrain.accuracy.mwpm_baseline import decode_with_mwpm
from cryobrain.accuracy.stim_harness import (
    count_logical_errors,
    surface_code_memory_circuit,
)
from cryobrain.stim.manifest import load_manifest
from cryobrain.types import ScenarioConfig

ROOT = Path.cwd()
MANIFEST_PATH = ROOT / "tasks" / "cryo_brain_decoder" / "stim" / "manifest.json"
OUT_PATH = ROOT / "artifacts" / "baselines" / "ler_baselines.json"


def _git(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        ).stdout.strip()
    except OSError:
        return ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mwpm_baseline(split: str, cfg: dict[str, object]) -> dict[str, object]:
    scenario = ScenarioConfig.from_dict(dict(cfg["scenario"]))  # type: ignore[arg-type]
    seed = int(cfg["seed"])
    shots = int(scenario.shots)
    circuit = surface_code_memory_circuit(
        scenario.distance,
        scenario.noise_rate,
        scenario.rounds,
    )
    sampler = circuit.compile_detector_sampler(seed=seed)
    dets, obs = sampler.sample(shots, separate_observables=True)
    predictions = decode_with_mwpm(circuit, np.asarray(dets, dtype=np.uint8))
    logical_errors = count_logical_errors(predictions, np.asarray(obs, dtype=np.uint8))
    ler = logical_errors / shots
    standard_error = math.sqrt((ler * (1.0 - ler)) / shots) if shots else 0.0
    epsilon_95 = 1.96 * standard_error

    return {
        "split": split,
        "decoder": "mwpm",
        "circuit": "stim.Circuit.generated(surface_code:rotated_memory_z)",
        "scenario": scenario.to_dict(),
        "seed": seed,
        "manifest_vectors": int(cfg["vectors"]),
        "shots": shots,
        "logical_errors": logical_errors,
        "logical_error_rate": ler,
        "standard_error": standard_error,
        "epsilon_95": epsilon_95,
    }


manifest = load_manifest(MANIFEST_PATH)
baselines = [
    _mwpm_baseline(split, dict(cfg))
    for split, cfg in dict(manifest["splits"]).items()  # type: ignore[index]
]
max_epsilon = max((float(row["epsilon_95"]) for row in baselines), default=0.0)

payload = {
    "schema_version": 1,
    "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
    "generated_by": "scripts/compute_ler_baselines_wsl.sh",
    "git": {
        "sha": _git(["rev-parse", "HEAD"]),
        "branch": _git(["branch", "--show-current"]),
        "dirty": bool(_git(["status", "--short"])),
    },
    "stim_manifest": {
        "path": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "version": int(manifest["version"]),  # type: ignore[index]
        "checksum": str(manifest["checksum"]),  # type: ignore[index]
        "sha256": _sha256(MANIFEST_PATH),
    },
    "source": {
        "kind": "mwpm_stim",
        "proxy_free": True,
        "decoder": "pymatching.Matching.from_stim_circuit",
        "sampler": "stim.CompiledDetectorSampler(seed=manifest split seed)",
    },
    "toolchain": {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "stim": getattr(stim, "__version__", "unknown"),
        "pymatching": getattr(pymatching, "__version__", "unknown"),
    },
    "reproducibility": {
        "epsilon_abs": max_epsilon,
        "epsilon_source": "max per-split 1.96 * sqrt(p * (1 - p) / shots)",
        "deterministic_sampling": True,
    },
    "baselines": baselines,
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"wrote {OUT_PATH.relative_to(ROOT)}")
for row in baselines:
    print(
        f"{row['split']}: MWPM LER={row['logical_error_rate']:.6f} "
        f"errors={row['logical_errors']}/{row['shots']} "
        f"epsilon95={row['epsilon_95']:.6f}"
    )
PY
