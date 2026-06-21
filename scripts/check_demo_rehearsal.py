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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _consistent_measurement_score(run_dir: Path) -> bool:
    measurement = _load_json(run_dir / "stim_ler_result.json")
    score = _load_json(run_dir / "score.json")
    score_measurement = score.get("measurement") if isinstance(score.get("measurement"), dict) else {}
    if "candidate_ler" in measurement and score.get("ler") is not None:
        if float(measurement["candidate_ler"]) != float(score["ler"]):
            return False
    if "suppression" in measurement and score.get("suppression") is not None:
        if float(measurement["suppression"]) != float(score["suppression"]):
            return False
    for key in ("candidate_ler", "suppression"):
        if key in measurement and key in score_measurement:
            if float(measurement[key]) != float(score_measurement[key]):
                return False
    return True


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.is_file()]
    if missing:
        print("C10 blocked — missing artifacts:")
        for path in missing:
            print(f"  - {path}")
        return 1

    climb = _load_json(ROOT / "artifacts" / "measured_climb.json")
    fifo = _load_json(ROOT / "artifacts" / "measured_fifo_climb.json")
    pareto = _load_json(ROOT / "artifacts" / "measured_pareto.json")
    demo = _load_json(ROOT / "artifacts" / "demo_bundle.json")

    assert climb.get("reward_source") == "score_measured"
    assert fifo.get("reward_source") == "measured_fifo_throughput"
    assert len(fifo.get("history", [])) >= 2, "FIFO climb needs 2+ measured steps for demo story"
    assert pareto.get("count", 0) >= 2, "C3 pareto needs 2+ points"
    assert demo.get("data_era") == "measured", "demo must be measured-only"
    assert demo.get("fifo_climb", {}).get("history"), "demo bundle must surface FIFO improvement"
    assert demo.get("improvement", {}).get("agents_keep_improving"), (
        "demo must show at least one improving measured track"
    )

    design_runs = sorted(path.parent for path in (ROOT / "artifacts" / "design_runs").glob("d*/score.json"))
    assert len(design_runs) >= 5, "submission needs 5+ design cycles"
    mismatched = [run.name for run in design_runs[:5] if not _consistent_measurement_score(run)]
    assert not mismatched, f"design run score/measurement mismatch: {mismatched}"

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
