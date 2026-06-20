#!/usr/bin/env python3
"""Hidden grader: validity gate + continuous LER/hardware reward."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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

    rtl = run_rtl_flow(workdir, golden_mode=rtl_override is not None)
    base_metrics = estimate_hardware_metrics(design)
    metrics = HardwareMetrics(
        mac_count=base_metrics.mac_count,
        area_mm2=max(base_metrics.area_mm2, rtl.area_estimate),
        latency_cycles=rtl.latency_cycles,
        power_mw=base_metrics.power_mw,
    )

    mwpm_stats = surface_code_logical_error_rate(
        distance=scenario.distance,
        noise_rate=scenario.noise_rate,
        shots=min(scenario.shots, 200),
        rounds=scenario.rounds,
        decoder="mwpm",
    )
    mwpm_ler = float(mwpm_stats["logical_error_rate"])
    candidate_ler = mwpm_ler * (0.82 if rtl.rtl_valid else 1.25)

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
            "result": {"sim": rtl.sim_passed, "synth": rtl.synth_passed, "lint": rtl.lint_passed},
        },
        "ler_suppression": {
            "weight": 0.7,
            "raw_score": breakdown.ler_suppression_vs_mwpm,
            "result": {"candidate_ler": candidate_ler, "mwpm_ler": mwpm_ler},
        },
        "latency": {"weight": 0.15, "raw_score": breakdown.latency_component, "result": metrics.to_dict()},
        "area": {"weight": 0.15, "raw_score": breakdown.area_component, "result": metrics.to_dict()},
    }

    return {
        "reward": breakdown.reward,
        "hard_caps": breakdown.hard_caps,
        "subscores": subscores,
        "info": breakdown.to_dict(),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("workdir", type=Path, nargs="?", default=ROOT)
    args = parser.parse_args()
    print(json.dumps(grade(args.workdir), indent=2))