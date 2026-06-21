#!/usr/bin/env python3
"""Seed verified-design memory from CP3 calibration rollouts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryobrain.calibration.cp3 import run_cp3_rollouts
from cryobrain.integrations.exa_rag import search_decoder_literature, seed_memory_tags
from cryobrain.memory.buffer import VerifiedDesignBuffer
from cryobrain.rl.local_trainer import _load_grade_fn


def main() -> None:
    buffer_path = ROOT / "artifacts" / "verified_memory.json"
    buffer = VerifiedDesignBuffer(buffer_path)
    task_root = ROOT / "tasks" / "cryo_brain_decoder"
    report = run_cp3_rollouts(_load_grade_fn(task_root), task_root)
    exa_tags = seed_memory_tags(search_decoder_literature())

    added = 0
    for rollout in report.get("rollouts", []):
        if not isinstance(rollout, dict):
            continue
        reward = float(rollout.get("reward", 0.0))
        if reward <= 0.0:
            continue
        scenario = rollout.get("scenario", {})
        design = rollout.get("design", {})
        if not isinstance(scenario, dict) or not isinstance(design, dict):
            continue
        if buffer.add_from_grade(
            design=design,
            reward=reward,
            metrics={"source_rollout": rollout.get("name", "cp3")},
            distance=int(scenario.get("distance", 3)),
            noise_rate=float(scenario.get("noise_rate", 0.001)),
            source="cp3_seed",
            tags=exa_tags,
        ):
            added += 1

    print(
        json.dumps(
            {
                "ok": True,
                "added": added,
                "buffer_size": len(buffer),
                "buffer_path": str(buffer_path),
                "exa_tags": exa_tags,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()