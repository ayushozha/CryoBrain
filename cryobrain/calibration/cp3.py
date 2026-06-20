"""CP3 multi-rollout reward calibration (SPEC §CP3)."""

from __future__ import annotations

import json
import math
import shutil
import statistics
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class RolloutVariant:
    name: str
    scenario: dict[str, object]
    design: dict[str, object]


# Ten deterministic perturbations around the d=3 starter policy.
# Spread hardware + Stim knobs; accuracy term is flat when benchmark exactness is fixed.
CP3_ROLLOUT_VARIANTS: tuple[RolloutVariant, ...] = (
    RolloutVariant("base", {}, {}),
    RolloutVariant("rounds_2", {"rounds": 2}, {}),
    RolloutVariant("rounds_5", {"rounds": 5}, {}),
    RolloutVariant("noise_35m", {"noise_rate": 0.035, "shots": 2500}, {}),
    RolloutVariant("budget_tight", {"max_area_mm2": 0.045, "max_latency_cycles": 48}, {}),
    RolloutVariant("budget_loose", {"max_area_mm2": 0.08, "max_latency_cycles": 96}, {}),
    RolloutVariant("pipeline_fast", {}, {"pipeline_depth": 2, "parallelism": 2}),
    RolloutVariant("pipeline_slow", {}, {"pipeline_depth": 16, "window_length": 12}),
    RolloutVariant("seed_sparse", {"benchmark_seed": 9001, "benchmark_vectors": 32}, {}),
    RolloutVariant("seed_dense", {"benchmark_seed": 4242, "benchmark_vectors": 96}, {}),
)


def _merge(base: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    merged.update(patch)
    return merged


def stage_workdir(task_root: Path, *, scenario: dict[str, object], design: dict[str, object]) -> Path:
    """Copy agent-facing task tree and bind scenario/design JSON."""
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-rollout-"))
    for name in ("Makefile", "filelist.f", "rtl", "dv", "synth", "design_config.json", "scenario.json"):
        src = task_root / name
        if not src.exists():
            continue
        dst = stage / name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    (stage / "scenario.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    (stage / "design_config.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    return stage


def summarize_rewards(rewards: list[float]) -> dict[str, float]:
    if not rewards:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "spread": 0.0}
    mean = statistics.fmean(rewards)
    std = statistics.pstdev(rewards) if len(rewards) > 1 else 0.0
    return {
        "mean": mean,
        "std": std,
        "min": min(rewards),
        "max": max(rewards),
        "spread": max(rewards) - min(rewards),
    }


def assess_cp3(
    rewards: list[float],
    *,
    band_lo: float = 0.20,
    band_hi: float = 0.50,
    min_std: float = 0.01,
    min_spread: float = 0.02,
) -> dict[str, object]:
    """Return CP3 pass/fail plus human-readable failure reasons."""
    stats = summarize_rewards(rewards)
    reasons: list[str] = []
    if not rewards:
        reasons.append("no_rollout_rewards")
    if stats["mean"] < band_lo:
        reasons.append(f"mean_below_{band_lo:.2f}")
    if stats["mean"] > band_hi:
        reasons.append(f"mean_above_{band_hi:.2f}")
    if stats["std"] < min_std and stats["spread"] < min_spread:
        reasons.append("insufficient_variance")
    if any(math.isclose(r, 0.0) for r in rewards) and all(math.isclose(r, 0.0) for r in rewards):
        reasons.append("all_zero_rewards")
    if any(math.isclose(r, 1.0) for r in rewards) and all(math.isclose(r, 1.0) for r in rewards):
        reasons.append("all_one_rewards")
    return {
        "ok": not reasons,
        "reasons": reasons,
        "stats": stats,
        "band": {"lo": band_lo, "hi": band_hi},
        "variance_floor": {"min_std": min_std, "min_spread": min_spread},
    }


def run_cp3_rollouts(
    grade_fn: Callable[[Path], dict[str, object]],
    task_root: Path,
    *,
    variants: tuple[RolloutVariant, ...] = CP3_ROLLOUT_VARIANTS,
) -> dict[str, Any]:
    base_scenario = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    base_design = json.loads((task_root / "design_config.json").read_text(encoding="utf-8"))

    rollouts: list[dict[str, object]] = []
    rewards: list[float] = []
    for variant in variants:
        scenario = _merge(base_scenario, variant.scenario)
        design = _merge(base_design, variant.design)
        workdir = stage_workdir(task_root, scenario=scenario, design=design)
        result = grade_fn(workdir)
        reward = float(result["reward"])
        rewards.append(reward)
        rollouts.append(
            {
                "name": variant.name,
                "reward": reward,
                "scenario": scenario,
                "design": design,
                "hard_caps": result.get("hard_caps", []),
                "benchmark_exactness": (
                    result.get("subscores", {})
                    .get("rtl_validity", {})
                    .get("result", {})
                    .get("benchmark_exactness")
                ),
            }
        )

    cp3 = assess_cp3(rewards)
    return {
        "rollouts": rollouts,
        "rewards": rewards,
        "cp3": cp3,
    }


def run_cp2_sanity(
    grade_fn: Callable[..., dict[str, object]],
    task_root: Path,
    hidden_root: Path,
) -> dict[str, object]:
    """CP2 anchor checks: wrong→0, starter mid-band, golden high."""
    workdir = stage_workdir(
        task_root,
        scenario=json.loads((task_root / "scenario.json").read_text(encoding="utf-8")),
        design=json.loads((task_root / "design_config.json").read_text(encoding="utf-8")),
    )
    wrong = grade_fn(
        workdir,
        rtl_override=hidden_root / "cryo_brain_decoder_wrong.sv",
        hidden_root=hidden_root,
    )
    starter = grade_fn(workdir, hidden_root=hidden_root)
    golden = grade_fn(
        workdir,
        rtl_override=hidden_root / "cryo_brain_decoder_golden.sv",
        hidden_root=hidden_root,
    )
    summary = {
        "wrong": float(wrong["reward"]),
        "starter": float(starter["reward"]),
        "golden": float(golden["reward"]),
    }
    summary["ok"] = (
        summary["wrong"] == 0.0
        and 0.20 <= summary["starter"] <= 0.50
        and summary["golden"] >= 0.60
    )
    return summary