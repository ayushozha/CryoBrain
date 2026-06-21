#!/usr/bin/env python3
"""Multi-cycle measured improvement marathon (SPEC-v6.1 ambitious loop).

Runs decoder, FIFO, memory A/B, planner, frontier sweep, export, and demo rebuild
in a loop — appending summaries to ``artifacts/improvement_marathon.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import shutil
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
MARATHON_RUNS = ARTIFACTS / "marathon_runs"
MARATHON_SUMMARY = ARTIFACTS / "measured_50_iteration_summary.json"
DECODER_STORE = ARTIFACTS / "marathon_decoder_memory.jsonl"
FIFO_STORE = ARTIFACTS / "marathon_fifo_memory.jsonl"

ARCHIVE_FILES = (
    "measured_climb.json",
    "measured_fifo_climb.json",
    "measured_memory_ab.json",
    "measured_pareto.json",
    "planner_climb.json",
    "verification_report.json",
)


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


def _summarize_memory_ab(path: Path) -> dict:
    data = _load_json(path)

    def _side(name: str) -> dict[str, object]:
        rows = data.get(name) if isinstance(data, dict) else []
        rewards = [
            float(row["suppression"])
            for row in rows or []
            if isinstance(row, dict) and row.get("suppression") is not None
        ]
        slope = 0.0
        if len(rewards) >= 2:
            slope = (rewards[-1] - rewards[0]) / max(len(rewards) - 1, 1)
        return {
            "count": len(rewards),
            "end_reward": rewards[-1] if rewards else None,
            "slope": round(slope, 6),
        }

    without = _side("without_memory")
    with_side = _side("with_memory")
    if with_side["end_reward"] is None or without["end_reward"] is None:
        return {
            "with": with_side["count"],
            "without": without["count"],
            "memory_wins": False,
            "status": "missing",
        }

    endpoint_delta = round(float(with_side["end_reward"]) - float(without["end_reward"]), 6)
    slope_delta = round(float(with_side["slope"]) - float(without["slope"]), 6)
    if endpoint_delta > 0:
        status = "memory_advantage"
    elif endpoint_delta < 0:
        status = "memory_regression"
    else:
        status = "memory_parity"
    return {
        "with": with_side["count"],
        "without": without["count"],
        "with_end_reward": with_side["end_reward"],
        "without_end_reward": without["end_reward"],
        "with_slope": with_side["slope"],
        "without_slope": without["slope"],
        "endpoint_delta": endpoint_delta,
        "slope_delta": slope_delta,
        "memory_wins": endpoint_delta > 0,
        "status": status,
    }


def _run_shell(cmd: list[str], *, label: str) -> int:
    print(f"\n=== {label} ===", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    return int(proc.returncode)


def _rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def _copy_artifact(src: Path, dst: Path) -> str | None:
    if not src.exists():
        return None
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return _rel(dst)


def _archive_cycle(summary: dict) -> dict[str, str]:
    cycle_dir = MARATHON_RUNS / f"cycle_{int(summary['cycle']):03d}"
    artifacts: dict[str, str] = {}
    for name in ARCHIVE_FILES:
        copied = _copy_artifact(ARTIFACTS / name, cycle_dir / name)
        if copied:
            artifacts[name] = copied
    design_runs = _copy_artifact(ARTIFACTS / "design_runs", cycle_dir / "design_runs")
    if design_runs:
        artifacts["design_runs"] = design_runs
    summary_path = cycle_dir / "summary.json"
    artifacts["summary"] = _rel(summary_path)
    summary["artifact_files"] = artifacts
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return artifacts


def _write_run_summary(
    *,
    summaries: list[dict],
    sponsor_report: dict[str, object] | None,
    cycles: int,
    steps: int,
    seed_base: int,
    min_iterations: int,
    status: str,
) -> None:
    payload = {
        "schema": "cryobrain.marathon_summary.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "requested_iterations": cycles,
        "min_iterations": min_iterations,
        "completed_iterations": len(summaries),
        "steps_per_agent": steps,
        "seed_base": seed_base,
        "required_sponsors": sponsor_report,
        "iteration_artifact_dirs": [s.get("artifact_dir") for s in summaries],
        "iterations": summaries,
        "evidence_policy": {
            "mock_artifacts_allowed": False,
            "cycle_archives": "Each completed iteration preserves measured runner artifacts under artifacts/marathon_runs/cycle_###.",
            "sponsor_gate": "When --require-sponsors is set, HUD, Exa, Fireworks, and Modal are checked before iteration 1.",
        },
        "validation_commands": [
            "python scripts/check_spec_v61_checkpoints.py",
            "python scripts/check_demo_rehearsal.py",
            f"python scripts/check_marathon_iterations.py --min-iterations {min_iterations}",
        ],
    }
    MARATHON_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    MARATHON_SUMMARY.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sponsor_evidence(
    sponsor_report: dict[str, object] | None,
    *,
    use_fireworks: bool,
    use_modal_measure: bool,
    backend: str,
) -> dict[str, object]:
    report = sponsor_report or {}
    return {
        "required_core_sponsors": {name: bool(report.get(name)) for name in CORE_SPONSORS},
        "exa": {
            "live_gate": bool(report.get("exa")),
            "hit_count": int(report.get("exa_hits") or 0),
            "urls": list(report.get("exa_urls") or []),
            "titles": list(report.get("exa_titles") or []),
        },
        "fireworks": {
            "live_gate": bool(report.get("fireworks")),
            "proposer_enabled": bool(use_fireworks),
        },
        "modal": {
            "live_gate": bool(report.get("modal")),
            "measure_enabled": bool(use_modal_measure),
            "backend": backend,
        },
        "hud": {
            "live_gate": bool(report.get("hud")),
        },
    }


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
    sponsor_report: dict[str, object] | None,
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
    planner = planner_trainer.run_planner_training(
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
        "artifact_dir": _rel(MARATHON_RUNS / f"cycle_{cycle:03d}"),
        "decoder": _summarize_climb(ARTIFACTS / "measured_climb.json"),
        "fifo": _summarize_climb(ARTIFACTS / "measured_fifo_climb.json", metric="throughput"),
        "memory_ab": _summarize_memory_ab(ARTIFACTS / "measured_memory_ab.json"),
        "planner": _summarize_climb(ARTIFACTS / "planner_climb.json") if (ARTIFACTS / "planner_climb.json").is_file() else None,
        "sponsors": {
            "fireworks": bool(use_fireworks),
            "modal_measure": bool(use_modal_measure),
            "exa_research": True,
        },
        "sponsor_evidence": _sponsor_evidence(
            sponsor_report,
            use_fireworks=use_fireworks,
            use_modal_measure=use_modal_measure,
            backend=backend,
        ),
        "step_logs": {
            "decoder": decoder.get("steps_log", []),
            "fifo": fifo.get("steps_log", []),
            "planner": planner.get("steps_log", []),
        },
        "decoder_memory_records": len(decoder_store),
        "fifo_memory_records": len(fifo_store),
        "decoder_attempted_this_run": len(decoder.get("steps_log", [])),
        "decoder_accepted_this_run": len(decoder.get("history", [])),
        "fifo_attempted_this_run": len(fifo.get("steps_log", [])),
        "fifo_accepted_this_run": len(fifo.get("history", [])),
        "planner_attempted_this_run": len(planner.get("steps_log", [])),
        "planner_accepted_this_run": len(planner.get("history", [])),
    }
    _archive_cycle(summary)

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
    parser.add_argument(
        "--min-iterations",
        type=int,
        default=None,
        help="minimum archived iterations required by the final marathon validator (defaults to --cycles)",
    )
    parser.add_argument("--fireworks", action="store_true", help="use Fireworks proposer when key set")
    parser.add_argument("--modal-measure", action="store_true", help="measure decoder/planner variants through Modal")
    parser.add_argument(
        "--require-sponsors",
        action="store_true",
        help="fail unless HUD, Exa, Fireworks, and Modal are available; implies --fireworks --modal-measure",
    )
    args = parser.parse_args(argv)
    min_iterations = args.cycles if args.min_iterations is None else args.min_iterations

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

    summaries: list[dict] = []
    for cycle in range(1, args.cycles + 1):
        summaries.append(run_cycle(
            cycle=cycle,
            steps=args.steps,
            seed=args.seed_base + cycle * 100,
            use_fireworks=args.fireworks,
            use_modal_measure=args.modal_measure,
            sponsor_report=sponsor_report,
        ))
        _write_run_summary(
            summaries=summaries,
            sponsor_report=sponsor_report,
            cycles=args.cycles,
            steps=args.steps,
            seed_base=args.seed_base,
            min_iterations=min_iterations,
            status="running" if cycle < args.cycles else "cycles_complete",
        )
        if cycle < args.cycles:
            time.sleep(max(0, args.pause_secs))

    _run_shell([sys.executable, str(ROOT / "scripts" / "check_spec_v61_checkpoints.py")], label="final checkpoint validation")
    _run_shell([sys.executable, str(ROOT / "scripts" / "check_demo_rehearsal.py")], label="final demo rehearsal")
    _run_shell(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_marathon_iterations.py"),
            "--min-iterations",
            str(min_iterations),
        ],
        label="final marathon iteration validation",
    )
    _write_run_summary(
        summaries=summaries,
        sponsor_report=sponsor_report,
        cycles=args.cycles,
        steps=args.steps,
        seed_base=args.seed_base,
        min_iterations=min_iterations,
        status="validation_passed",
    )
    print("=== IMPROVEMENT MARATHON COMPLETE ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
