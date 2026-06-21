#!/usr/bin/env python3
"""SPEC2 CP5: memory-on vs memory-off training overlay."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryobrain.rl.config import TrainConfig
from cryobrain.rl.local_trainer import run_graded_training


def _slope(history: list[dict[str, object]]) -> float:
    if len(history) < 2:
        return 0.0
    start = float(history[0].get("reward", 0.0))
    end = float(history[-1].get("reward", 0.0))
    return (end - start) / max(len(history) - 1, 1)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Memory A/B climb chart overlay (SPEC2 CP5)")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    buffer_path = artifacts / "verified_memory.json"
    if not buffer_path.is_file():
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "seed_memory.py")], check=True, cwd=ROOT)

    base = TrainConfig(
        steps=args.steps,
        seed=args.seed,
        memory_buffer=str(buffer_path),
    )
    no_mem = run_graded_training(
        TrainConfig(
            steps=base.steps,
            seed=base.seed,
            curriculum=base.curriculum,
            output=str(artifacts / "climb_chart_no_memory.json"),
            designs_output=str(artifacts / "designs_no_memory.json"),
            memory_enabled=False,
        )
    )
    with_mem = run_graded_training(
        TrainConfig(
            steps=base.steps,
            seed=base.seed,
            curriculum=base.curriculum,
            output=str(artifacts / "climb_chart_memory.json"),
            designs_output=str(artifacts / "designs_memory.json"),
            memory_enabled=True,
            memory_buffer=str(buffer_path),
            exa_seed=True,
        )
    )

    overlay = {
        "ok": True,
        "steps": args.steps,
        "without_memory": {
            "end_reward": no_mem["summary"]["end_reward"],
            "slope": round(_slope(no_mem["history"]), 6),
            "path": str(artifacts / "climb_chart_no_memory.json"),
        },
        "with_memory": {
            "end_reward": with_mem["summary"]["end_reward"],
            "slope": round(_slope(with_mem["history"]), 6),
            "memory_records": with_mem.get("memory_records", 0),
            "path": str(artifacts / "climb_chart_memory.json"),
        },
        "memory_wins": float(with_mem["summary"]["end_reward"])
        >= float(no_mem["summary"]["end_reward"]),
    }
    out = artifacts / "memory_ab_overlay.json"
    out.write_text(json.dumps(overlay, indent=2), encoding="utf-8")
    print(json.dumps(overlay, indent=2))


if __name__ == "__main__":
    main()