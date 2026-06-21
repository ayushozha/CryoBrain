#!/usr/bin/env python3
"""Multi-cycle measured improvement marathon (SPEC-v6.1 ambitious loop).

Runs decoder, FIFO, memory A/B, planner, frontier sweep, export, and demo rebuild
in a loop — appending summaries to ``artifacts/improvement_marathon.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
sys.path.insert(0, str(ROOT))

from cryobrain.memory.store import MemoryStore  # noqa: E402
from cryobrain.rl import fifo_loop, local_trainer, planner_trainer  # noqa: E402
from cryobrain.rl.modal_measure import make_modal_score_fn  # noqa: E402
from scripts.check_sponsors import CORE_SPONSORS, build_report  # noqa: E402

MARATHON_LOG = ARTIFACTS / "improvement_marathon.jsonl"
DECODER_STORE = ARTIFACTS / "marathon_decoder_memory.jsonl"
FIFO_STORE = ARTIFACTS / "marathon_fifo_memory.jsonl"


def _load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize_climb(path: Path, *, metric: str = "suppression") -> dict:
    data = _load_json(path)
    if not isinstance(data, dict):
        return {"path": str(path), "accepted": 0, "metric": metric}
    hist = data.get("history") or []
    if not hist:
        return {"path": str(path), "accepted": 0, "metric": metric, "reward_source": data.get("reward_source")}
    start = hist[0].get(metric, hist[0].get("suppression", 0.0))
    end = hist[-1].get(metric, hist[-1].get("suppression", 0.0))
    return {
        "path": str(path.relative_to(ROOT)),
        "accepted": len(hist),
        "metric": metric,
        "start": start,
        "end": end,
        "delta": round(float(end) - float(start), 6),
        "reward_source": data.get("reward_source"),
    }


def _run_shell(cmd: list[str], *, label: str) -> int:
    print(f"\n=== {label} ===", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    return int(proc.returncode)


def _require_core_sponsors() -> dict[str, object]:
    report = build_report()
    missing = [name for name in CORE_SPONSORS if not report.get(name)]
    if missing:
        raise RuntimeError(f"missing required sponsor platform(s): {', '.join(missing)}")
    return report


def run_cycle(
    *,
    cycle: int,
    steps: int,
    seed: int,
    use_fireworks: bool,
    use_modal_measure: bool,
) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    decoder_store = MemoryStore(DECODER_STORE)
    fifo_store = MemoryStore(FIFO_STORE)

    proposer = local_trainer.fireworks_proposer if use_fireworks else local_trainer.deterministic_proposer
    score_fn = make_modal_score_fn(force_local=False) if use_modal_measure else local_trainer.score_measured
    backend = "modal+stim+verilator+yosys" if use_modal_measure else "verilator+stim+yosys"

    print(f"\n=== cycle {cycle}: decoder climb ({steps} steps, persistent memory) ===", flush=True)
    decoder = local_trainer.run_measured_training(
        steps=steps,
        seed=seed,
        proposer=proposer,
        score_fn=score_fn,
        store=decoder_store,
        climb_path=ARTIFACTS / "measured_climb.json",
        backend=backend,
    )

    print(f"\n=== cycle {cycle}: memory A/B ({steps} steps) ===", flush=True)
    local_trainer.run_memory_ab(steps=steps, seed=seed + 17, score_fn=score_fn)

    print(f"\n=== cycle {cycle}: FIFO climb ({steps} steps, persistent memory) ===", flush=True)
    fifo = fifo_loop.run_fifo_training(
        steps=steps,
        seed=seed + 31,
        store=fifo_store,
        climb_path=ARTIFACTS / "measured_fifo_climb.json",
    )

    print(f"\n=== cycle {cycle}: planner climb ({steps} steps, sponsor measured) ===", flush=True)
    planner_trainer.run_planner_training(
        steps=steps,
        seed=seed + 47,
        score_fn=score_fn,
        store=decoder_store,
        climb_path=ARTIFACTS / "planner_climb.json",
        backend=backend,
    )

    _run_shell(["bash", "scripts/run_frontier_sweep_wsl.sh"], label=f"cycle {cycle}: frontier sweep")
    _run_shell(["bash", "scripts/export_spec_v61_wsl.sh"], label=f"cycle {cycle}: export design_runs")
    _run_shell([sys.executable, str(ROOT / "scripts" / "build_demo.py")], label=f"cycle {cycle}: demo rebuild")

    summary = {
        "cycle": cycle,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "seed": seed,
        "decoder": _summarize_climb(ARTIFACTS / "measured_climb.json"),
        "fifo": _summarize_climb(ARTIFACTS / "measured_fifo_climb.json", metric="throughput"),
        "memory_ab": {
            "with": len((_load_json(ARTIFACTS / "measured_memory_ab.json") or {}).get("with_memory") or []),
            "without": len((_load_json(ARTIFACTS / "measured_memory_ab.json") or {}).get("without_memory") or []),
        },
        "planner": _summarize_climb(ARTIFACTS / "planner_climb.json") if (ARTIFACTS / "planner_climb.json").is_file() else None,
        "sponsors": {
            "fireworks": bool(use_fireworks),
            "modal_measure": bool(use_modal_measure),
            "exa_research": True,
        },
        "decoder_memory_records": len(decoder_store),
        "fifo_memory_records": len(fifo_store),
        "decoder_accepted_this_run": len(decoder.get("history", [])),
        "fifo_accepted_this_run": len(fifo.get("history", [])),
    }

    MARATHON_LOG.parent.mkdir(parents=True, exist_ok=True)
    with MARATHON_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(summary) + "\n")

    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=6, help="number of improvement cycles")
    parser.add_argument("--steps", type=int, default=10, help="measured steps per agent per cycle")
    parser.add_argument("--seed-base", type=int, default=0)
    parser.add_argument("--pause-secs", type=int, default=20, help="pause between cycles")
    parser.add_argument("--fireworks", action="store_true", help="use Fireworks proposer when key set")
    parser.add_argument("--modal-measure", action="store_true", help="measure decoder/planner variants through Modal")
    parser.add_argument(
        "--require-sponsors",
        action="store_true",
        help="fail unless HUD, Exa, Fireworks, and Modal are available; implies --fireworks --modal-measure",
    )
    args = parser.parse_args(argv)

    sponsor_report = _require_core_sponsors() if args.require_sponsors else None
    if args.require_sponsors:
        args.fireworks = True
        args.modal_measure = True

    print(
        f"Improvement marathon: {args.cycles} cycles x {args.steps} steps "
        f"(log -> {MARATHON_LOG})",
        flush=True,
    )
    if sponsor_report is not None:
        print(json.dumps({"required_sponsors": sponsor_report}, indent=2), flush=True)

    for cycle in range(1, args.cycles + 1):
        run_cycle(
            cycle=cycle,
            steps=args.steps,
            seed=args.seed_base + cycle * 100,
            use_fireworks=args.fireworks,
            use_modal_measure=args.modal_measure,
        )
        if cycle < args.cycles:
            time.sleep(max(0, args.pause_secs))

    _run_shell([sys.executable, str(ROOT / "scripts" / "check_spec_v61_checkpoints.py")], label="final checkpoint validation")
    _run_shell([sys.executable, str(ROOT / "scripts" / "check_demo_rehearsal.py")], label="final demo rehearsal")
    print("=== IMPROVEMENT MARATHON COMPLETE ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
