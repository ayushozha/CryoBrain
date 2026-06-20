#!/usr/bin/env python3
"""CP6 helper — Pareto frontier + RSI distance curriculum charts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryobrain.artifacts.pareto import generate_all_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="CP6: generate Pareto + curriculum artifacts")
    parser.add_argument("--climb-chart", type=Path, default=Path("artifacts/climb_chart.json"))
    parser.add_argument("--designs", type=Path, default=Path("artifacts/designs.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()

    outputs = generate_all_artifacts(
        climb_chart_path=args.climb_chart,
        designs_path=args.designs,
        artifacts_dir=args.out_dir,
    )
    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())