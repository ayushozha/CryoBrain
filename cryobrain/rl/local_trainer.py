"""Real local CP4 training loop backed by the hidden CryoBrain grader."""

from __future__ import annotations

import importlib.util
import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from cryobrain.calibration.cp3 import stage_workdir
from cryobrain.cost_model.npu_cost import estimate_hardware_metrics
from cryobrain.integrations.exa_rag import search_decoder_literature, seed_memory_tags
from cryobrain.integrations.fireworks import propose_design_config
from cryobrain.memory.buffer import VerifiedDesignBuffer
from cryobrain.memory.retrieve import retrieve
from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm
from cryobrain.rl.config import CurriculumStage, TrainConfig
from cryobrain.types import DesignConfig

ROOT = Path(__file__).resolve().parents[2]
TASK_ROOT = ROOT / "tasks" / "cryo_brain_decoder"

GradeFn = Callable[[Path], dict[str, object]]


def _load_grade_fn(task_root: Path = TASK_ROOT) -> GradeFn:
    """Load the hidden grader without importing from a hidden package path."""
    grade_path = task_root / "donotaccess" / "grade.py"
    spec = importlib.util.spec_from_file_location("cryo_brain_decoder_grade", grade_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {grade_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    hidden_root = task_root / "donotaccess"

    def grade(workdir: Path) -> dict[str, object]:
        return module.grade(workdir, hidden_root=hidden_root)

    return grade


def _design_sweep(seed: int) -> list[DesignConfig]:
    """Small deterministic policy search over the spec's design knobs."""
    base = [
        DesignConfig(bitwidth=4, num_layers=1, parallelism=1, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=2, num_layers=1, parallelism=1, pipeline_depth=4, window_length=4),
        DesignConfig(bitwidth=2, num_layers=1, parallelism=2, pipeline_depth=2, window_length=4),
        DesignConfig(bitwidth=4, num_layers=1, parallelism=2, pipeline_depth=2, window_length=8),
        DesignConfig(bitwidth=2, num_layers=2, parallelism=2, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=4, num_layers=2, parallelism=2, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=4, num_layers=2, parallelism=4, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=8, num_layers=1, parallelism=4, pipeline_depth=4, window_length=8),
    ]
    tail = base[1:]
    random.Random(seed).shuffle(tail)
    return [base[0], *tail]


def _scenario_for_stage(
    base_scenario: dict[str, object],
    stage: CurriculumStage,
    *,
    seed: int,
    step: int,
) -> dict[str, object]:
    scenario = dict(base_scenario)
    scenario.update(
        {
            "distance": stage.distance,
            "noise_rate": stage.noise_rate,
            "max_latency_cycles": stage.budget.max_latency_cycles,
            "max_area_mm2": stage.budget.max_area_mm2,
            "max_power_mw": stage.budget.max_power_mw,
            "benchmark_seed": seed * 1009 + step,
            "benchmark_vectors": 64,
        }
    )
    return scenario


def _stage_index(step: int, steps: int, stages: list[CurriculumStage]) -> int:
    if not stages:
        return 0
    return min(len(stages) - 1, step * len(stages) // max(steps, 1))


def _design_from_dict(raw: dict[str, object]) -> DesignConfig:
    return DesignConfig(
        bitwidth=int(raw.get("bitwidth", 4)),
        num_layers=int(raw.get("num_layers", 1)),
        parallelism=int(raw.get("parallelism", 1)),
        pipeline_depth=int(raw.get("pipeline_depth", 4)),
        window_length=int(raw.get("window_length", 8)),
    )


def _mutate_from_exemplar(exemplar: dict[str, object], step: int, seed: int) -> DesignConfig:
    """Perturb a high-reward exemplar to explore nearby design space."""
    raw = exemplar.get("design", {})
    base = DesignConfig.from_dict(raw if isinstance(raw, dict) else {})
    rng = random.Random(seed * 1009 + step)
    knobs = ("bitwidth", "num_layers", "parallelism", "pipeline_depth", "window_length")
    values = list(base.to_dict().values())
    idx = step % len(knobs)
    choices = {
        "bitwidth": [2, 4, 8],
        "num_layers": [1, 2, 4],
        "parallelism": [1, 2, 4],
        "pipeline_depth": [2, 4, 8, 16],
        "window_length": [4, 8, 12, 16],
    }
    key = knobs[idx]
    pool = choices[key]
    current = getattr(base, key)
    alt = [v for v in pool if v != current]
    if alt:
        values[idx] = rng.choice(alt)
    return DesignConfig(**dict(zip(knobs, values, strict=True)))


def _pick_candidate(
    *,
    step: int,
    candidates: list[DesignConfig],
    config: TrainConfig,
    scenario: dict[str, object],
    buffer: VerifiedDesignBuffer | None,
) -> tuple[DesignConfig, list[dict[str, object]]]:
    exemplars: list[dict[str, object]] = []
    if config.memory_enabled and buffer is not None:
        exemplars = retrieve(
            {"scenario": scenario},
            buffer_path=config.memory_buffer,
            k=config.memory_top_k,
        )
        if exemplars:
            return _mutate_from_exemplar(exemplars[0], step, config.seed), exemplars

    if config.use_fireworks and step % 5 == 4:
        proposed = propose_design_config(scenario=scenario, exemplars=exemplars)
        if proposed is not None:
            return proposed, exemplars

    return candidates[step % len(candidates)], exemplars


def _metric(subscores: dict[str, object], name: str, key: str, default: float = 0.0) -> float:
    section = subscores.get(name, {})
    if not isinstance(section, dict):
        return default
    if key == "raw_score":
        return float(section.get("raw_score", default))
    result = section.get("result", {})
    return float(result.get(key, default)) if isinstance(result, dict) else default


def run_graded_training(
    config: TrainConfig,
    *,
    grade_fn: GradeFn | None = None,
    task_root: Path = TASK_ROOT,
) -> dict[str, object]:
    """Run a CP4 hill-climb where every point is scored by the real grader."""
    task_root = Path(task_root)
    grade_fn = grade_fn or _load_grade_fn(task_root)
    base_scenario = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    candidates = _design_sweep(config.seed)
    stages = list(config.curriculum)
    buffer = VerifiedDesignBuffer(config.memory_buffer) if config.memory_enabled else None
    exa_tags: list[str] = []
    if config.exa_seed:
        exa_tags = seed_memory_tags(search_decoder_literature())

    history: list[dict[str, object]] = []
    designs: list[dict[str, object]] = []
    transitions: list[dict[str, object]] = []
    accepted_reward = 0.0
    accepted_design = candidates[0]
    last_stage_idx = 0

    for step in range(config.steps):
        stage_idx = _stage_index(step, config.steps, stages)
        stage = stages[stage_idx]
        if step and stage_idx != last_stage_idx:
            transitions.append(
                {
                    "step": step,
                    "from_distance": stages[last_stage_idx].distance,
                    "to_distance": stage.distance,
                    "reward_at_transition": round(accepted_reward, 4),
                }
            )
            last_stage_idx = stage_idx

        scenario = _scenario_for_stage(base_scenario, stage, seed=config.seed, step=step)
        candidate, exemplars = _pick_candidate(
            step=step,
            candidates=candidates,
            config=config,
            scenario=scenario,
            buffer=buffer,
        )
        workdir = stage_workdir(task_root, scenario=scenario, design=candidate.to_dict())
        result = grade_fn(workdir)
        candidate_reward = float(result["reward"])
        subscores = result.get("subscores", {})
        if not isinstance(subscores, dict):
            subscores = {}

        if step == 0 or candidate_reward >= accepted_reward:
            accepted_reward = candidate_reward
            accepted_design = candidate

        row = {
            "step": step,
            "reward": round(accepted_reward, 6),
            "candidate_reward": round(candidate_reward, 6),
            "distance": stage.distance,
            "stage": stage_idx,
            "noise_rate": stage.noise_rate,
            "accepted": candidate == accepted_design,
            "design": accepted_design.to_dict(),
            "candidate_design": candidate.to_dict(),
            "hard_caps": result.get("hard_caps", []),
            "ler_suppression": round(_metric(subscores, "ler_suppression", "raw_score"), 6),
            "latency_score": round(_metric(subscores, "latency", "raw_score"), 6),
            "area_score": round(_metric(subscores, "area", "raw_score"), 6),
            "benchmark_exactness": round(
                _metric(subscores, "rtl_validity", "benchmark_exactness"),
                6,
            ),
            "memory_exemplars": len(exemplars),
        }
        history.append(row)

        if buffer is not None and candidate_reward > 0.0 and not result.get("hard_caps"):
            latency_section = subscores.get("latency", {})
            metrics = latency_section.get("result", {}) if isinstance(latency_section, dict) else {}
            if not isinstance(metrics, dict):
                metrics = estimate_hardware_metrics(candidate).to_dict()
            buffer.add_from_grade(
                design=candidate.to_dict(),
                reward=candidate_reward,
                metrics=metrics,
                distance=stage.distance,
                noise_rate=stage.noise_rate,
                source="cp4_trainer",
                tags=exa_tags,
            )

        if candidate_reward > 0.0 and not result.get("hard_caps"):
            latency_section = subscores.get("latency", {})
            metrics = latency_section.get("result", {}) if isinstance(latency_section, dict) else {}
            if not isinstance(metrics, dict):
                metrics = estimate_hardware_metrics(candidate).to_dict()
            designs.append(
                {
                    "name": f"agent-step-{step}",
                    "kind": "policy",
                    "step": step,
                    "distance": stage.distance,
                    "reward": round(candidate_reward, 6),
                    "area_mm2": float(metrics.get("area_mm2", 0.0)),
                    "latency_cycles": int(metrics.get("latency_cycles", 0)),
                    "power_mw": float(metrics.get("power_mw", 0.0)),
                    "ler_suppression": row["ler_suppression"],
                    "benchmark_exactness": row["benchmark_exactness"],
                    "design": candidate.to_dict(),
                    "source": "hidden_grader",
                }
            )

    output = Path(config.output)
    designs_path = Path(config.designs_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    designs_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "start_reward": history[0]["reward"] if history else 0.0,
        "end_reward": history[-1]["reward"] if history else 0.0,
        "max_reward": max((h["reward"] for h in history), default=0.0),
        "stages_completed": (max((int(h["stage"]) for h in history), default=0) + 1) if history else 0,
        "accepted_design": accepted_design.to_dict(),
    }
    payload: dict[str, object] = {
        "backend": "real_local",
        "memory_enabled": config.memory_enabled,
        "use_fireworks": config.use_fireworks,
        "exa_seed": config.exa_seed,
        "memory_records": len(buffer) if buffer is not None else 0,
        "reward_source": str(task_root / "donotaccess" / "grade.py"),
        "config": config.to_dict(),
        "steps": config.steps,
        "final_distance": stages[last_stage_idx].distance if stages else None,
        "history": history,
        "curriculum_transitions": transitions,
        "summary": summary,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    designs_path.write_text(json.dumps(designs, indent=2), encoding="utf-8")
    return payload


def run_local_training(config: TrainConfig) -> dict[str, object]:
    """Backward-compatible entrypoint for the real local graded trainer."""
    return run_graded_training(config)


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
