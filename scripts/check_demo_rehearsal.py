#!/usr/bin/env python3
"""C10: verify measured artifact bundle is demo-ready (SPEC-v6.1 §10)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "artifacts" / "measured_climb.json",
    ROOT / "artifacts" / "measured_memory_ab.json",
    ROOT / "artifacts" / "measured_pareto.json",
    ROOT / "artifacts" / "swarm" / "event_log.jsonl",
    ROOT / "artifacts" / "verification_report.json",
    ROOT / "demo" / "index.html",
    ROOT / "artifacts" / "demo_bundle.json",
]


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.is_file()]
    if missing:
        print("C10 blocked — missing artifacts:")
        for path in missing:
            print(f"  - {path}")
        return 1

    climb = json.loads((ROOT / "artifacts" / "measured_climb.json").read_text(encoding="utf-8"))
    pareto = json.loads((ROOT / "artifacts" / "measured_pareto.json").read_text(encoding="utf-8"))
    demo = json.loads((ROOT / "artifacts" / "demo_bundle.json").read_text(encoding="utf-8"))

    assert climb.get("reward_source") == "score_measured"
    assert pareto.get("count", 0) >= 2, "C3 pareto needs 2+ points"
    assert demo.get("data_era") == "measured", "demo must be measured-only"

    design_runs = list((ROOT / "artifacts" / "design_runs").glob("d*/score.json"))
    assert len(design_runs) >= 3, "C2 needs 3+ design cycles"

    print("C10 PASS: demo bundle complete and measured-only")
    print(f"  climb steps: {len(climb.get('history', []))}")
    print(f"  pareto points: {pareto.get('count')}")
    print(f"  design_runs: {len(design_runs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())