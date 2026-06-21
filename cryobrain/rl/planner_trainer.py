"""Planner measured climb trainer (SPEC-v6 P-train2).

Thin loop: Planner chooses search direction -> Architect applies plan ->
measured proposal step (``score_measured`` only). Planner earns reward from
the measured suppression **delta** its chosen experiments achieve.

Artifacts:
  * ``artifacts/planner_climb.json`` — same climb row schema as
    ``measured_climb.json``, plus ``planner_source`` tag.

End-to-end real climb: ``scripts/run_planner_climb_wsl.sh`` (Linux + EDA).
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from cryobrain.grader.score import score_measured
from cryobrain.memory.store import MemoryStore
from cryobrain.rl.local_trainer import _load_scenario, _write_json
from cryobrain.rl.proposal_loop import ROOT, TASK_ROOT, ScoreFn, run_proposal_step
from cryobrain.swarm.event_bus import EventBus
from cryobrain.swarm.planner import Planner

ARTIFACTS = ROOT / "artifacts"
DEFAULT_CLIMB = ARTIFACTS / "planner_climb.json"
PLANNER_SOURCE = "cryobrain.swarm.planner"


def run_planner_training(
    *,
    steps: int,
    seed: int = 0,
    score_fn: ScoreFn = score_measured,
    store: MemoryStore | None = None,
    task_root: Path = TASK_ROOT,
    climb_path: Path | None = DEFAULT_CLIMB,
    backend: str = "verilator+stim+yosys",
    bus: EventBus | None = None,
) -> dict[str, Any]:
    """Run Planner -> Architect -> measured step for ``steps`` iterations."""
    scenario = _load_scenario(task_root)
    rng = random.Random(seed)
    store = store if store is not None else MemoryStore()
    planner = Planner(seed=seed, bus=bus if bus is not None else EventBus())

    best_suppression = float("-inf")
    history: list[dict[str, Any]] = []
    plans_log: list[dict[str, Any]] = []
    steps_log: list[dict[str, Any]] = []

    for step in range(steps):
        plan = planner.plan(
            step,
            store=store,
            climb_history=history,
            plans_log=plans_log,
        )
        design = planner.apply_plan(plan, rng)
        result = run_proposal_step(
            step=step,
            design=design,
            scenario=scenario,
            store=store,
            score_fn=score_fn,
            backend=backend,
            task_root=task_root,
            bus=planner.bus,
        )

        prev_best = best_suppression
        planner_reward = (
            float(result.suppression - prev_best)
            if result.valid and history
            else (float(result.suppression) if result.valid and not history else 0.0)
        )

        accepted = result.valid and (result.suppression > best_suppression or not history)
        if accepted:
            best_suppression = result.suppression
            history.append(result.climb_row())

        plan_row = {
            "step": step,
            "knob": plan["knob"],
            "direction": plan["direction"],
            "planner_reward": planner_reward,
            "design": design.to_dict(),
            "accepted": accepted,
        }
        plans_log.append(plan_row)

        steps_log.append(
            {
                "step": step,
                "plan": plan,
                "design": design.to_dict(),
                "reward": result.reward,
                "candidate_ler": result.candidate_ler,
                "suppression": result.suppression,
                "planner_reward": planner_reward,
                "valid": result.valid,
                "accepted": accepted,
                "recorded": result.recorded,
                "layers_passed": result.layers_passed,
                "rtl_hash": result.rtl_hash,
            }
        )

        if result.valid:
            planner.bus.emit(
                planner.AGENT_NAME,
                "observe",
                str(plan["design_id"]),
                {
                    "knob": plan["knob"],
                    "planner_reward": planner_reward,
                    "suppression": result.suppression,
                    "candidate_ler": result.candidate_ler,
                },
            )

    payload: dict[str, Any] = {
        "backend": backend,
        "reward_source": "score_measured",
        "planner_source": PLANNER_SOURCE,
        "steps": steps,
        "memory_records": len(store),
        "history": history,
        "plans_log": plans_log,
        "steps_log": steps_log,
    }
    if climb_path is not None:
        _write_json(
            Path(climb_path),
            {k: payload[k] for k in ("backend", "reward_source", "planner_source", "steps", "history")},
        )
    return payload


def _empty_climb(steps: int, backend: str) -> dict[str, Any]:
    return {
        "backend": backend,
        "reward_source": "score_measured",
        "planner_source": PLANNER_SOURCE,
        "steps": steps,
        "history": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steps", type=int, default=5, help="number of planner-directed measured steps")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--climb", type=Path, default=DEFAULT_CLIMB)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="emit an empty schema-shaped planner climb artifact (Windows-safe)",
    )
    args = parser.parse_args(argv)

    backend = "verilator+stim+yosys"
    if args.dry_run:
        _write_json(args.climb, _empty_climb(args.steps, backend))
        print(f"[dry-run] wrote empty schema-shaped planner climb to {args.climb}")
        print("Real measured planner climb runs in WSL: scripts/run_planner_climb_wsl.sh")
        return 0

    result = run_planner_training(
        steps=args.steps,
        seed=args.seed,
        climb_path=args.climb,
        backend=backend,
    )
    accepted = len(result["history"])
    print(
        f"planner climb: {accepted}/{args.steps} accepted, "
        f"{result['memory_records']} memory records, climb -> {args.climb}"
    )
    if not accepted:
        print(
            "No valid measured variants. On Windows (no Verilator/Yosys) this is expected; "
            "run scripts/run_planner_climb_wsl.sh in WSL for the real planner climb, "
            "or use --dry-run."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
