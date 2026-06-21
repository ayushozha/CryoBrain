#!/usr/bin/env python3
"""C10: verify measured artifact bundle is demo-ready (SPEC-v6.1 §10)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "artifacts" / "measured_climb.json",
    ROOT / "artifacts" / "measured_fifo_climb.json",
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
    fifo = json.loads((ROOT / "artifacts" / "measured_fifo_climb.json").read_text(encoding="utf-8"))
    pareto = json.loads((ROOT / "artifacts" / "measured_pareto.json").read_text(encoding="utf-8"))
    demo = json.loads((ROOT / "artifacts" / "demo_bundle.json").read_text(encoding="utf-8"))

    assert climb.get("reward_source") == "score_measured"
    assert fifo.get("reward_source") == "measured_fifo_throughput"
    assert len(fifo.get("history", [])) >= 2, "FIFO climb needs 2+ measured steps for demo story"
    assert pareto.get("count", 0) >= 2, "C3 pareto needs 2+ points"
    assert demo.get("data_era") == "measured", "demo must be measured-only"
    assert demo.get("fifo_climb", {}).get("history"), "demo bundle must surface FIFO improvement"
    assert demo.get("improvement", {}).get("agents_keep_improving"), (
        "demo must show at least one improving measured track"
    )

    design_runs = list((ROOT / "artifacts" / "design_runs").glob("d*/score.json"))
    assert len(design_runs) >= 3, "C2 needs 3+ design cycles"

    fifo_hist = fifo.get("history", [])
    fifo_trend = fifo_hist[-1]["throughput"] - fifo_hist[0]["throughput"] if len(fifo_hist) >= 2 else 0.0

    print("C10 PASS: demo bundle complete and measured-only")
    print(f"  decoder climb steps: {len(climb.get('history', []))}")
    print(f"  fifo climb steps: {len(fifo_hist)} (trend {fifo_trend:+.4f})")
    print(f"  pareto points: {pareto.get('count')}")
    print(f"  design_runs: {len(design_runs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())