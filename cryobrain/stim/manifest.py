"""Versioned Stim benchmark splits for measured LER (SPEC-v5 G2)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cryobrain.types import ScenarioConfig

MANIFEST_VERSION = 1
TASK_STIM_ROOT = Path(__file__).resolve().parents[2] / "tasks" / "cryo_brain_decoder" / "stim"
DEFAULT_MANIFEST = TASK_STIM_ROOT / "manifest.json"


def _scenario_dict(scenario: ScenarioConfig) -> dict[str, int | float]:
    return scenario.to_dict()


def default_manifest() -> dict[str, object]:
    base = ScenarioConfig(distance=3, noise_rate=0.02, shots=1000, rounds=3)
    return {
        "version": MANIFEST_VERSION,
        "splits": {
            "train": {
                "seed": 1729,
                "vectors": 64,
                "scenario": _scenario_dict(base),
            },
            "holdout": {
                "seed": 4242,
                "vectors": 64,
                "scenario": _scenario_dict(base),
            },
        },
    }


def manifest_checksum(data: dict[str, object]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def write_manifest(path: Path | None = None) -> Path:
    path = path or DEFAULT_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    data = default_manifest()
    data["checksum"] = manifest_checksum(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def load_manifest(path: Path | None = None) -> dict[str, object]:
    path = path or DEFAULT_MANIFEST
    if not path.is_file():
        write_manifest(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = manifest_checksum({k: v for k, v in data.items() if k != "checksum"})
    if data.get("checksum") != expected:
        raise ValueError(f"stim manifest checksum mismatch: {path}")
    return data


def split_config(name: str, path: Path | None = None) -> dict[str, object]:
    data = load_manifest(path)
    splits = data.get("splits", {})
    if name not in splits:
        raise KeyError(f"unknown stim split {name!r}; expected one of {sorted(splits)}")
    return dict(splits[name])


def holdout_paths(path: Path | None = None) -> list[str]:
    holdout = split_config("holdout", path)
    return [f"holdout:seed={holdout['seed']}:vectors={holdout['vectors']}"]