"""Local RL co-design stub — produces climb chart + design rollouts (SPEC F6/F7)."""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict
from pathlib import Path

from cryobrain.cost_model.npu_cost import estimate_hardware_metrics
from cryobrain.reward.compute_reward import compute_reward, ler_suppression_vs_mwpm
from cryobrain.rl.config import CurriculumStage, TrainConfig
from cryobrain.types import DesignConfig


def _stage_difficulty(stage: CurriculumStage) -> float:
    """Higher distance + noise makes the decode problem harder."""
    return 0.12 * (stage.distance - 3) + 35.0 * stage.noise_rate


def _sample_design(rng: random.Random, step: int) -> DesignConfig:
    """Policy-improving design sweep — bitwidth/layers/parallelism knobs."""
    bitwidth = rng.choice([2, 4, 4, 8])
    num_layers = rng.choice([1, 2, 2, 3])
    parallelism = rng.choice([1, 1, 2, 4])
    pipeline_depth = rng.choice([2, 4, 4, 8])
    window_length = 4 + (step % 5) * 2
    return DesignConfig(
        bitwidth=bitwidth,
        num_layers=num_layers,
        parallelism=parallelism,
        pipeline_depth=pipeline_depth,
        window_length=window_length,
    )


def _simulate_ler(
    *,
    stage: CurriculumStage,
    design: DesignConfig,
    policy_gain: float,
    rng: random.Random,
) -> tuple[float, float]:
    """Synthetic MWPM + candidate LER for stub training (no Stim round-trip)."""
    base_mwpm = 0.018 + _stage_difficulty(stage)
    mwpm_ler = base_mwpm * (1.0 + 0.05 * rng.random())
    capacity = (
        0.08 * design.num_layers
        + 0.04 * math.log2(max(design.bitwidth, 2))
        + 0.03 * math.log2(max(design.parallelism, 1))
    )
    candidate_ler = mwpm_ler * max(0.55, 1.0 - policy_gain - capacity + 0.02 * rng.random())
    return mwpm_ler, candidate_ler


def run_local_training(config: TrainConfig) -> dict[str, object]:
    """Run curriculum-aware stub RL and write climb_chart.json + designs.json."""
    rng = random.Random(config.seed)
    stages = list(config.curriculum)
    stage_idx = 0
    policy_gain = 0.0
    history: list[dict[str, object]] = []
    transitions: list[dict[str, object]] = []
    designs: list[dict[str, object]] = []

    steps_per_stage = max(8, config.steps // max(len(stages), 1))
    steps_in_stage = 0

    for step in range(config.steps):
        stage = stages[stage_idx]
        design = _sample_design(rng, step)
        metrics = estimate_hardware_metrics(design)

        # Policy improves over time within each curriculum stage.
        policy_gain = min(0.42, policy_gain + 0.006 + 0.002 * (step % 7) / 7.0)
        mwpm_ler, candidate_ler = _simulate_ler(
            stage=stage,
            design=design,
            policy_gain=policy_gain,
            rng=rng,
        )

        breakdown = compute_reward(
            rtl_valid=True,
            metrics=metrics,
            budget=stage.budget,
            candidate_ler=candidate_ler,
            mwpm_ler=mwpm_ler,
        )
        reward = breakdown.reward

        history.append(
            {
                "step": step,
                "reward": round(reward, 4),
                "distance": stage.distance,
                "stage": stage_idx,
                "noise_rate": stage.noise_rate,
                "ler_suppression": round(breakdown.ler_suppression_vs_mwpm, 4),
            }
        )

        if breakdown.meets_budget and breakdown.ler_suppression_vs_mwpm > 0.05:
            designs.append(
                {
                    "name": f"agent-step-{step}",
                    "step": step,
                    "distance": stage.distance,
                    "area_mm2": round(metrics.area_mm2, 6),
                    "latency_cycles": metrics.latency_cycles,
                    "power_mw": round(metrics.power_mw, 4),
                    "ler_suppression": round(breakdown.ler_suppression_vs_mwpm, 4),
                    "reward": round(reward, 4),
                    "design": design.to_dict(),
                }
            )

        steps_in_stage += 1

        # Escalate d3→5→7 after minimum stage dwell and reward clears threshold.
        at_last_stage = stage_idx >= len(stages) - 1
        stage_mature = steps_in_stage >= steps_per_stage
        cleared = reward >= stage.min_reward_to_advance
        if not at_last_stage and steps_in_stage >= max(6, steps_per_stage // 2) and (cleared or stage_mature):
            transitions.append(
                {
                    "step": step,
                    "from_distance": stage.distance,
                    "to_distance": stages[stage_idx + 1].distance,
                    "reward_at_transition": round(reward, 4),
                }
            )
            stage_idx += 1
            steps_in_stage = 0
            policy_gain *= 0.62  # re-optimization dip at harder distance (F7 story)

    output = Path(config.output)
    designs_path = Path(config.designs_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    designs_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, object] = {
        "backend": "local_stub",
        "config": config.to_dict(),
        "steps": config.steps,
        "final_distance": stages[stage_idx].distance,
        "history": history,
        "curriculum_transitions": transitions,
        "summary": {
            "start_reward": history[0]["reward"] if history else 0.0,
            "end_reward": history[-1]["reward"] if history else 0.0,
            "max_reward": max((h["reward"] for h in history), default=0.0),
            "stages_completed": stage_idx + 1,
        },
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    designs_path.write_text(json.dumps(designs, indent=2), encoding="utf-8")
    return payload


def baseline_designs() -> list[dict[str, object]]:
    """Anchors for Pareto plot: MWPM + neural reference + starter config."""
    starter = DesignConfig(bitwidth=4, num_layers=2, parallelism=1, pipeline_depth=4, window_length=8)
    starter_metrics = estimate_hardware_metrics(starter)
    neural = DesignConfig(bitwidth=8, num_layers=4, parallelism=1, pipeline_depth=16, window_length=16)
    neural_metrics = estimate_hardware_metrics(neural)
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
            "name": "starter",
            "kind": "policy",
            "area_mm2": round(starter_metrics.area_mm2, 6),
            "latency_cycles": starter_metrics.latency_cycles,
            "power_mw": round(starter_metrics.power_mw, 4),
            "ler_suppression": round(ler_suppression_vs_mwpm(0.017, mwpm_ler), 4),
            "reward": 0.32,
            "design": asdict(starter),
        },
        {
            "name": "neural-ref",
            "kind": "baseline",
            "area_mm2": round(neural_metrics.area_mm2, 6),
            "latency_cycles": neural_metrics.latency_cycles,
            "power_mw": round(neural_metrics.power_mw, 4),
            "ler_suppression": round(ler_suppression_vs_mwpm(0.008, mwpm_ler), 4),
            "reward": 0.0,
        },
    ]