#!/usr/bin/env python3
"""Hidden grader: validity gate + continuous LER/hardware reward."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_BENCHMARK_TO_SUPPRESSION = 0.50


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _stage_with_rtl(workdir: Path, rtl_src: Path) -> Path:
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-grade-"))
    shutil.copytree(workdir, stage, dirs_exist_ok=True, symlinks=True)
    shutil.copy2(rtl_src, stage / "rtl" / "cryo_brain_decoder.sv")
    return stage


def grade(
    workdir: Path,
    rtl_override: Path | None = None,
    hidden_root: Path | None = None,
) -> dict[str, object]:
    if rtl_override is not None:
        workdir = _stage_with_rtl(workdir, rtl_override)

    from cryobrain.accuracy.stim_harness import surface_code_logical_error_rate
    from cryobrain.cost_model.npu_cost import HardwareMetrics, estimate_hardware_metrics
    from cryobrain.reward.compute_reward import compute_reward
    from cryobrain.rtl_grader.flow import run_rtl_flow
    from cryobrain.types import CryoBudget, DesignConfig, ScenarioConfig

    scenario_raw = _load_json(workdir / "scenario.json")
    scenario = ScenarioConfig.from_dict(scenario_raw)
    design = DesignConfig.from_dict(_load_json(workdir / "design_config.json"))
    budget = CryoBudget(
        max_latency_cycles=int(scenario_raw.get("max_latency_cycles", 64)),
        max_area_mm2=float(scenario_raw.get("max_area_mm2", 0.06)),
        max_power_mw=float(scenario_raw.get("max_power_mw", 8.0)),
    )

    rtl = run_rtl_flow(workdir, golden_mode=rtl_override is not None and "golden" in rtl_override.name.lower())
    base_metrics = estimate_hardware_metrics(design)
    metrics = HardwareMetrics(
        mac_count=base_metrics.mac_count,
        area_mm2=max(base_metrics.area_mm2, rtl.area_estimate),
        latency_cycles=rtl.latency_cycles if rtl.rtl_valid else base_metrics.latency_cycles,
        power_mw=base_metrics.power_mw,
    )

    benchmark_noise_rate = max(scenario.noise_rate, 0.02)
    initial_shots = max(scenario.shots, 1000)
    mwpm_stats = surface_code_logical_error_rate(
        distance=scenario.distance,
        noise_rate=benchmark_noise_rate,
        shots=initial_shots,
        rounds=scenario.rounds,
        decoder="mwpm",
    )
    mwpm_ler = float(mwpm_stats["logical_error_rate"])
    benchmark_suppression = min(0.95, _BENCHMARK_TO_SUPPRESSION * rtl.benchmark_exactness)
    candidate_ler = mwpm_ler * (1.0 - benchmark_suppression) if mwpm_ler > 0 else 0.0
    ler_factor = candidate_ler / mwpm_ler if mwpm_ler > 0 else 0.0

    breakdown = compute_reward(
        rtl_valid=rtl.rtl_valid,
        metrics=metrics,
        budget=budget,
        candidate_ler=candidate_ler,
        mwpm_ler=mwpm_ler,
    )

    subscores = {
        "rtl_validity": {
            "weight": 0.0,
            "raw_score": 1.0 if rtl.rtl_valid else 0.0,
            "result": {
                "sim": rtl.sim_passed,
                "synth": rtl.synth_passed,
                "lint": rtl.lint_passed,
                "tools_available": rtl.tools_available,
                "benchmark_vectors": rtl.benchmark_vectors,
                "benchmark_failures": rtl.benchmark_failures,
                "benchmark_exactness": rtl.benchmark_exactness,
                "benchmark_confidence": rtl.benchmark_confidence,
            },
        },
        "ler_suppression": {
            "weight": 0.7,
            "raw_score": breakdown.ler_suppression_vs_mwpm,
            "result": {
                "candidate_ler": candidate_ler,
                "mwpm_ler": mwpm_ler,
                "ler_factor": ler_factor,
                "benchmark_noise_rate": benchmark_noise_rate,
                "benchmark_to_suppression": _BENCHMARK_TO_SUPPRESSION,
            },
        },
        "latency": {"weight": 0.15, "raw_score": breakdown.latency_component, "result": metrics.to_dict()},
        "area": {"weight": 0.15, "raw_score": breakdown.area_component, "result": metrics.to_dict()},
    }

    return {
        "reward": breakdown.reward,
        "hard_caps": breakdown.hard_caps,
        "subscores": subscores,
        "info": {
            **breakdown.to_dict(),
            "rtl_logs": rtl.logs,
        },
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("workdir", type=Path, nargs="?", default=ROOT)
    args = parser.parse_args()
    print(json.dumps(grade(args.workdir), indent=2))
