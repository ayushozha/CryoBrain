#!/usr/bin/env python3
"""Validate auditable sponsor-backed improvement-marathon iterations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.check_spec_v61_checkpoints import MANDATORY_RUN_FILES  # noqa: E402

CORE_SPONSORS = ("hud", "exa", "fireworks", "modal")
SUMMARY_PATH = ROOT / "artifacts" / "measured_50_iteration_summary.json"
REQUIRED_ARCHIVE_ENTRIES = (
    "summary.json",
    "measured_climb.json",
    "measured_fifo_climb.json",
    "measured_memory_ab.json",
    "measured_pareto.json",
    "planner_climb.json",
    "verification_report.json",
    "design_runs",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_path(ref: str) -> Path | None:
    path = Path(ref)
    candidate = path if path.is_absolute() else ROOT / path
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate


def _memory_summary_from_artifact(path: Path) -> dict[str, Any] | None:
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    def _side(name: str) -> dict[str, Any]:
        rows = data.get(name) if isinstance(data.get(name), list) else []
        rewards = [
            float(row["suppression"])
            for row in rows
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
    if without["end_reward"] is None or with_side["end_reward"] is None:
        return None

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


def _check_memory_ab(iteration: dict[str, Any], cycle_dir: Path, label: str) -> list[str]:
    errors: list[str] = []
    memory = iteration.get("memory_ab") if isinstance(iteration.get("memory_ab"), dict) else {}
    expected = _memory_summary_from_artifact(cycle_dir / "measured_memory_ab.json")
    if expected is None:
        return [f"{label}: archived measured_memory_ab.json is not a usable measured A/B artifact"]

    required = (
        "with",
        "without",
        "with_end_reward",
        "without_end_reward",
        "with_slope",
        "without_slope",
        "endpoint_delta",
        "slope_delta",
        "memory_wins",
        "status",
    )
    missing = [key for key in required if key not in memory]
    if missing:
        errors.append(f"{label}: memory_ab summary missing {missing}")
        return errors

    for key in ("with", "without"):
        if int(memory.get(key) or 0) != int(expected[key]):
            errors.append(f"{label}: memory_ab {key} count does not match archived artifact")
    for key in ("with_end_reward", "without_end_reward", "with_slope", "without_slope", "endpoint_delta", "slope_delta"):
        if abs(float(memory.get(key) or 0.0) - float(expected[key])) > 1e-6:
            errors.append(f"{label}: memory_ab {key} does not match archived artifact")
    if bool(memory.get("memory_wins")) != bool(expected["memory_wins"]):
        errors.append(f"{label}: memory_ab memory_wins must be a strict positive endpoint delta")
    if memory.get("status") != expected["status"]:
        errors.append(f"{label}: memory_ab status does not match archived artifact")
    return errors


def _check_design_runs(path: Path, prefix: str) -> list[str]:
    errors: list[str] = []
    run_dirs = sorted(item for item in path.glob("d*") if item.is_dir())
    if len(run_dirs) < 5:
        return [f"{prefix}: need 5+ design runs, have {len(run_dirs)}"]
    for run_dir in run_dirs[:5]:
        missing = [name for name in MANDATORY_RUN_FILES if not (run_dir / name).is_file()]
        if missing:
            errors.append(f"{prefix}/{run_dir.name}: missing {missing}")
    return errors


def _check_iteration(iteration: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    label = f"iteration {index}"
    artifact_dir = iteration.get("artifact_dir")
    if not artifact_dir:
        return [f"{label}: missing artifact_dir"]
    cycle_dir = _as_path(str(artifact_dir))
    if cycle_dir is None:
        return [f"{label}: artifact_dir escapes repository root: {artifact_dir}"]
    if not cycle_dir.is_dir():
        return [f"{label}: artifact_dir missing on disk: {artifact_dir}"]

    for name in REQUIRED_ARCHIVE_ENTRIES:
        path = cycle_dir / name
        if not path.exists():
            errors.append(f"{label}: missing archived {name}")
    if (cycle_dir / "design_runs").is_dir():
        errors.extend(_check_design_runs(cycle_dir / "design_runs", label))

    sponsors = iteration.get("sponsors") if isinstance(iteration.get("sponsors"), dict) else {}
    if not (sponsors.get("fireworks") and sponsors.get("modal_measure") and sponsors.get("exa_research")):
        errors.append(f"{label}: missing per-iteration sponsor flags")
    evidence = iteration.get("sponsor_evidence") if isinstance(iteration.get("sponsor_evidence"), dict) else {}
    core = evidence.get("required_core_sponsors") if isinstance(evidence.get("required_core_sponsors"), dict) else {}
    missing_core = [name for name in CORE_SPONSORS if not core.get(name)]
    if missing_core:
        errors.append(f"{label}: sponsor_evidence missing core sponsor gate(s): {missing_core}")
    exa = evidence.get("exa") if isinstance(evidence.get("exa"), dict) else {}
    if not exa.get("live_gate") or int(exa.get("hit_count") or 0) < 1:
        errors.append(f"{label}: sponsor_evidence has no live Exa hit")
    fireworks = evidence.get("fireworks") if isinstance(evidence.get("fireworks"), dict) else {}
    if not (fireworks.get("live_gate") and fireworks.get("proposer_enabled")):
        errors.append(f"{label}: sponsor_evidence has no Fireworks proposer proof")
    modal = evidence.get("modal") if isinstance(evidence.get("modal"), dict) else {}
    if not (modal.get("live_gate") and modal.get("measure_enabled") and "modal" in str(modal.get("backend", ""))):
        errors.append(f"{label}: sponsor_evidence has no Modal measurement proof")

    decoder = iteration.get("decoder") if isinstance(iteration.get("decoder"), dict) else {}
    fifo = iteration.get("fifo") if isinstance(iteration.get("fifo"), dict) else {}
    planner = iteration.get("planner") if isinstance(iteration.get("planner"), dict) else {}
    if decoder.get("reward_source") != "score_measured":
        errors.append(f"{label}: decoder reward_source is not score_measured")
    if fifo.get("reward_source") != "measured_fifo_throughput":
        errors.append(f"{label}: fifo reward_source is not measured_fifo_throughput")
    if planner.get("reward_source") != "score_measured":
        errors.append(f"{label}: planner reward_source is not score_measured")
    errors.extend(_check_memory_ab(iteration, cycle_dir, label))

    steps = int(iteration.get("steps") or 0)
    step_logs = iteration.get("step_logs") if isinstance(iteration.get("step_logs"), dict) else {}
    for key in ("decoder_attempted_this_run", "fifo_attempted_this_run", "planner_attempted_this_run"):
        if int(iteration.get(key) or 0) < steps:
            errors.append(f"{label}: {key} is below steps")
    for key in ("decoder", "fifo", "planner"):
        log = step_logs.get(key) if isinstance(step_logs.get(key), list) else []
        if len(log) < steps:
            errors.append(f"{label}: {key} step_log has {len(log)} rows, expected {steps}")
        invalid = [row.get("step") for row in log if isinstance(row, dict) and not row.get("valid")]
        if invalid:
            errors.append(f"{label}: {key} step_log has invalid measured rows: {invalid}")
    return errors


def check_summary(path: Path = SUMMARY_PATH, *, min_iterations: int = 50) -> list[str]:
    if not path.is_file():
        return [f"missing marathon summary: {path}"]
    data = _load_json(path)
    if not isinstance(data, dict):
        return [f"{path}: summary must be a JSON object"]

    errors: list[str] = []
    completed = int(data.get("completed_iterations") or 0)
    iterations = data.get("iterations") if isinstance(data.get("iterations"), list) else []
    if completed < min_iterations:
        errors.append(f"need {min_iterations}+ completed iterations, have {completed}")
    if len(iterations) < completed:
        errors.append(f"summary lists {len(iterations)} iterations but completed_iterations={completed}")

    sponsor_report = data.get("required_sponsors") if isinstance(data.get("required_sponsors"), dict) else {}
    missing = [name for name in CORE_SPONSORS if not sponsor_report.get(name)]
    if missing:
        errors.append(f"required sponsor gate missing or false: {missing}")

    artifact_dirs = [str(item) for item in data.get("iteration_artifact_dirs") or [] if item]
    if len(set(artifact_dirs)) != len(artifact_dirs):
        errors.append("iteration_artifact_dirs contains duplicates")

    for index, iteration in enumerate(iterations[:completed], start=1):
        if not isinstance(iteration, dict):
            errors.append(f"iteration {index}: not a JSON object")
            continue
        errors.extend(_check_iteration(iteration, index))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--min-iterations", type=int, default=50)
    parser.add_argument("--require-sponsors", action="store_true", help="compatibility flag; sponsors are always required")
    parser.add_argument("--require-artifacts", action="store_true", help="compatibility flag; artifacts are always required")
    args = parser.parse_args(argv)

    errors = check_summary(args.summary, min_iterations=args.min_iterations)
    print("Marathon iteration validation")
    print("-" * 48)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("-" * 48)
        print("BLOCKED")
        return 1
    print(f"PASS: {args.min_iterations}+ sponsor-backed iterations have archived measured artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
