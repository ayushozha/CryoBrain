#!/usr/bin/env python3
"""CP4 helper — kick off CryoBrain RL training (Modal or local stub)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryobrain.rl.config import TrainConfig
from cryobrain.rl.modal_train import run_training


def main() -> int:
    parser = argparse.ArgumentParser(description="CP4: CryoBrain RL training launcher")
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts/climb_chart.json"))
    parser.add_argument("--designs-output", type=Path, default=Path("artifacts/designs.json"))
    parser.add_argument("--config", type=Path, help="Optional TrainConfig JSON")
    parser.add_argument("--local", action="store_true", help="Force local stub")
    args = parser.parse_args()

    if args.config and args.config.is_file():
        config = TrainConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))
    else:
        config = TrainConfig(
            steps=args.steps,
            seed=args.seed,
            output=str(args.output),
            designs_output=str(args.designs_output),
        )

    result = run_training(config, force_local=args.local)
    print(json.dumps(result, indent=2))

    history = result.get("history", [])
    if isinstance(history, list) and len(history) >= 2:
        start = float(history[0].get("reward", 0.0))  # type: ignore[union-attr]
        end = float(history[-1].get("reward", 0.0))  # type: ignore[union-attr]
        if end <= start:
            print("WARNING: reward did not trend up — check CP3 calibration before long runs", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())