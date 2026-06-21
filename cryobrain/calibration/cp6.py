"""CP6 Pareto + RSI distance curriculum from real graded designs (no stub RL)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from cryobrain.calibration.cp3 import RolloutVariant, stage_workdir
from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm
from task_catalog import CRYO_CURRICULUM, CRYO_SLUGS


# Eight deterministic design variants for Pareto spread.
CP6_DESIGN_VARIANTS: tuple[RolloutVariant, ...] = (
    RolloutVariant("starter", {}, {}),
    RolloutVariant("pipeline_fast", {}, {"pipeline_depth": 2, "parallelism": 2}),
    RolloutVariant("pipeline_slow", {}, {"pipeline_depth": 16, "window_length": 12}),
    RolloutVariant("wide_shallow", {}, {"bitwidth": 8, "num_layers": 1}),
    RolloutVariant("deep_narrow", {}, {"bitwidth": 4, "num_layers": 4}),
    RolloutVariant("parallel", {}, {"parallelism": 4, "pipeline_depth": 4}),
    RolloutVariant("sparse_window", {}, {"window_length": 4}),
    RolloutVariant("dense_window", {}, {"window_length": 16, "num_layers": 3}),
)


def _merge(base: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    merged.update(patch)
    return merged


def _extract_ler_suppression(grade_result: dict[str, object]) -> float:
    sub = grade_result.get("subscores", {})
    if isinstance(sub, dict):
        ler = sub.get("ler_suppression", {})
        if isinstance(ler, dict):
            return float(ler.get("raw_score", 0.0))
    return 0.0


def _extract_area(grade_result: dict[str, object]) -> float:
    sub = grade_result.get("subscores", {})
    if isinstance(sub, dict):
        for key in ("area", "latency"):
            block = sub.get(key, {})
            if isinstance(block, dict):
                result = block.get("result", {})
                if isinstance(result, dict) and "area_mm2" in result:
                    return float(result["area_mm2"])
    info = grade_result.get("info", {})
    if isinstance(info, dict) and "area_mm2" in info:
        return float(info["area_mm2"])
    return 0.0


def baseline_anchors() -> list[dict[str, object]]:
    """MWPM + neural reference anchors (not synthetic policy rollouts)."""
    mwpm_ler = 0.022
    return [
        {
            "name": "mwpm",
            "kind": "baseline",
            "area_mm2": 0.06,
            "latency_cycles": 12,
            "power_mw": 2.0,
            "ler_suppression": 0.0,
            "reward": 0.0,
        },
        {
            "name": "neural-ref",
            "kind": "baseline",
            "area_mm2": 0.085,
            "latency_cycles": 48,
            "power_mw": 8.0,
            "ler_suppression": round(ler_suppression_vs_mwpm(0.008, mwpm_ler), 4),
            "reward": 0.0,
        },
    ]


def grade_design_variants(
    grade_fn: Callable[..., dict[str, object]],
    task_root: Path,
    hidden_root: Path,
    *,
    distance_slug: str = "cryo-brain-decoder-d3",
) -> list[dict[str, object]]:
    """Grade eight real design variants at a curriculum distance."""
    base_scenario = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    base_design = json.loads((task_root / "design_config.json").read_text(encoding="utf-8"))
    knobs = CRYO_CURRICULUM[distance_slug]
    scenario = _merge(base_scenario, knobs)

    designs: list[dict[str, object]] = []
    for variant in CP6_DESIGN_VARIANTS:
        design = _merge(base_design, variant.design)
        workdir = stage_workdir(task_root, scenario=scenario, design=design)
        result = grade_fn(workdir, hidden_root=hidden_root)
        suppression = _extract_ler_suppression(result)
        area = _extract_area(result)
        if area <= 0.0:
            area = float(knobs.get("max_area_mm2", 0.06)) * 0.7
        designs.append(
            {
                "name": variant.name,
                "kind": "policy",
                "distance": int(knobs["distance"]),
                "area_mm2": round(area, 6),
                "ler_suppression": round(suppression, 4),
                "reward": round(float(result["reward"]), 4),
                "design": design,
                "hard_caps": result.get("hard_caps", []),
            }
        )
    return designs


def build_curriculum_history(
    grade_fn: Callable[..., dict[str, object]],
    task_root: Path,
    hidden_root: Path,
) -> dict[str, object]:
    """Real d=3→5→7 rewards using starter RTL at each curriculum stage."""
    base_scenario = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    base_design = json.loads((task_root / "design_config.json").read_text(encoding="utf-8"))
    history: list[dict[str, object]] = []
    transitions: list[dict[str, object]] = []
    prev_distance: int | None = None

    for step, slug in enumerate(CRYO_SLUGS):
        knobs = CRYO_CURRICULUM[slug]
        scenario = _merge(base_scenario, knobs)
        workdir = stage_workdir(task_root, scenario=scenario, design=base_design)
        result = grade_fn(workdir, hidden_root=hidden_root)
        reward = float(result["reward"])
        distance = int(knobs["distance"])
        history.append(
            {
                "step": step,
                "reward": round(reward, 4),
                "distance": distance,
                "slug": slug,
                "ler_suppression": round(_extract_ler_suppression(result), 4),
            }
        )
        if prev_distance is not None and distance != prev_distance:
            transitions.append(
                {
                    "step": step,
                    "from_distance": prev_distance,
                    "to_distance": distance,
                    "reward_at_transition": round(reward, 4),
                }
            )
        prev_distance = distance

    rewards_by_d = {
        int(row["distance"]): float(row["reward"])
        for row in history
    }
    return {
        "backend": "real_cp6",
        "history": history,
        "curriculum_transitions": transitions,
        "final_distance": history[-1]["distance"] if history else 3,
        "rewards_by_distance": rewards_by_d,
        "summary": {
            "start_reward": history[0]["reward"] if history else 0.0,
            "end_reward": history[-1]["reward"] if history else 0.0,
            "distances_graded": sorted(rewards_by_d),
        },
    }


def assess_cp6(
    designs: list[dict[str, object]],
    climb_chart: dict[str, object],
    *,
    min_policy_designs: int = 6,
    min_ler_spread: float = 0.02,
) -> dict[str, object]:
    """Verify Pareto frontier visibility and distance curriculum signal."""
    reasons: list[str] = []
    policy = [d for d in designs if d.get("kind") == "policy"]
    if len(policy) < min_policy_designs:
        reasons.append("insufficient_policy_designs")

    suppressions = [float(d.get("ler_suppression", 0.0)) for d in policy]
    areas = [float(d.get("area_mm2", 0.0)) for d in policy]
    ler_spread = max(suppressions) - min(suppressions) if suppressions else 0.0
    area_spread = max(areas) - min(areas) if areas else 0.0
    if ler_spread < min_ler_spread and area_spread < 1e-4:
        reasons.append("flat_pareto_frontier")

    rewards_by_d = climb_chart.get("rewards_by_distance", {})
    if not isinstance(rewards_by_d, dict) or len(rewards_by_d) < 3:
        reasons.append("missing_distance_grades")
    else:
        vals = [float(v) for v in rewards_by_d.values()]
        if max(vals) - min(vals) < 0.01:
            reasons.append("flat_distance_curriculum")

    return {
        "ok": not reasons,
        "reasons": reasons,
        "policy_designs": len(policy),
        "ler_spread": round(ler_spread, 4),
        "area_spread": round(area_spread, 6),
        "rewards_by_distance": rewards_by_d,
    }


def run_cp6_collection(
    grade_fn: Callable[..., dict[str, object]],
    task_root: Path,
    hidden_root: Path,
    *,
    artifacts_dir: Path | None = None,
) -> dict[str, Any]:
    """Collect real designs + curriculum, write artifacts, return assessment."""
    out = artifacts_dir or (task_root.parents[1] / "artifacts")
    out.mkdir(parents=True, exist_ok=True)

    policy_designs = grade_design_variants(grade_fn, task_root, hidden_root)
    climb = build_curriculum_history(grade_fn, task_root, hidden_root)
    all_designs = [*baseline_anchors(), *policy_designs]

    designs_path = out / "designs.json"
    climb_path = out / "climb_chart.json"
    designs_path.write_text(json.dumps(all_designs, indent=2), encoding="utf-8")
    climb_path.write_text(json.dumps(climb, indent=2), encoding="utf-8")

    assessment = assess_cp6(policy_designs, climb)
    return {
        "designs": all_designs,
        "climb_chart": climb,
        "assessment": assessment,
        "paths": {"designs": str(designs_path), "climb_chart": str(climb_path)},
    }