"""Measured reward scoring — replaces proxy grade path (SPEC-v5 G10 / MP2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.cost_model.npu_cost import HardwareMetrics
from cryobrain.reward.compute_reward import compute_reward, ler_suppression_vs_mwpm
from cryobrain.rtl_grader.synth_metrics import synth_metrics
from cryobrain.types import CryoBudget, DesignConfig, ScenarioConfig
from cryobrain.verify.l1_functional import run_l1
from cryobrain.verify.l4_synth import run_l4
from cryobrain.verify.l5_budget import run_l5

_GRADING_MIN_NOISE_RATE = 0.02
_GRADING_MIN_SHOTS = 1000


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _grading_scenario(scenario: ScenarioConfig, *, shots: int) -> ScenarioConfig:
    return ScenarioConfig(
        distance=scenario.distance,
        noise_rate=max(scenario.noise_rate, _GRADING_MIN_NOISE_RATE),
        shots=max(shots, scenario.shots, _GRADING_MIN_SHOTS),
        rounds=scenario.rounds,
    )


def score_measured(
    workdir: Path,
    *,
    shots: int = 1000,
    seed: int = 1729,
) -> dict[str, Any]:
    """Score a decoder workdir using measured LER + Yosys metrics + L1/L4/L5 gates."""
    workdir = Path(workdir)
    scenario_raw = _load_json(workdir / "scenario.json")
    scenario = ScenarioConfig.from_dict(scenario_raw)
    design = DesignConfig.from_dict(_load_json(workdir / "design_config.json"))
    budget = CryoBudget(
        max_latency_cycles=int(scenario_raw.get("max_latency_cycles", 64)),
        max_area_mm2=float(scenario_raw.get("max_area_mm2", 0.06)),
        max_power_mw=float(scenario_raw.get("max_power_mw", 8.0)),
    )

    rtl_path = workdir / "rtl" / "cryo_brain_decoder.sv"
    if not rtl_path.is_file():
        return {
            "reward": 0.0,
            "valid": False,
            "ler": 1.0,
            "area_um2": 0.0,
            "latency_cycles": 0,
            "power_mw": 0.0,
            "layers_passed": [],
            "hard_caps": ["rtl_missing"],
            "mwpm_ler": 0.0,
            "suppression": 0.0,
            "design": design.to_dict(),
            "source": "measured",
        }

    layers_passed: list[str] = []
    l1 = run_l1(rtl_path)
    if l1["passed"]:
        layers_passed.append("L1")

    graded = _grading_scenario(scenario, shots=shots)
    measure = measure_candidate_ler(rtl_path, graded, shots=shots, seed=seed)
    if measure["rtl_valid"] and measure["benchmark_vectors"] > 0:
        layers_passed.append("L2")

    l4 = run_l4(rtl_path)
    if l4["passed"]:
        layers_passed.append("L4")

    synth = synth_metrics(rtl_path)
    l5 = run_l5(rtl_path, budget=budget)
    if l5["passed"]:
        layers_passed.append("L5")

    rtl_valid = {"L1", "L2", "L4", "L5"}.issubset(layers_passed)
    metrics = HardwareMetrics(
        mac_count=0,
        area_mm2=synth["area_um2"] / 1_000_000.0,
        latency_cycles=synth["latency_cycles"],
        power_mw=synth["power_mw_est"],
    )
    breakdown = compute_reward(
        rtl_valid=rtl_valid,
        metrics=metrics,
        budget=budget,
        candidate_ler=float(measure["candidate_ler"]),
        mwpm_ler=float(measure["mwpm_ler"]),
    )

    return {
        "reward": breakdown.reward,
        "valid": rtl_valid,
        "ler": float(measure["candidate_ler"]),
        "area_um2": float(synth["area_um2"]),
        "latency_cycles": int(synth["latency_cycles"]),
        "power_mw": float(synth["power_mw_est"]),
        "layers_passed": layers_passed,
        "hard_caps": breakdown.hard_caps,
        "mwpm_ler": float(measure["mwpm_ler"]),
        "suppression": breakdown.ler_suppression_vs_mwpm,
        "latency_component": breakdown.latency_component,
        "area_component": breakdown.area_component,
        "design": design.to_dict(),
        "measurement": dict(measure),
        "synth": dict(synth),
        "l1_log": l1["log_path"],
        "l4_log": l4["log_path"],
        "source": "measured",
    }


def grade_result_to_subscores(score: dict[str, Any], *, metrics: HardwareMetrics) -> dict[str, object]:
    """Map ``score_measured`` output to hidden-grader subscore layout."""
    return {
        "rtl_validity": {
            "weight": 0.0,
            "raw_score": 1.0 if score["valid"] else 0.0,
            "result": {
                "layers_passed": score["layers_passed"],
                "hard_caps": score["hard_caps"],
                "source": score["source"],
            },
        },
        "ler_suppression": {
            "weight": 0.7,
            "raw_score": score["suppression"],
            "result": {
                "candidate_ler": score["ler"],
                "mwpm_ler": score["mwpm_ler"],
                "suppression": score["suppression"],
                "decoder": "measured_verilator",
                "measurement": score.get("measurement"),
            },
        },
        "latency": {
            "weight": 0.15,
            "raw_score": score.get("latency_component", 0.0),
            "result": metrics.to_dict(),
        },
        "area": {
            "weight": 0.15,
            "raw_score": score.get("area_component", 0.0),
            "result": {
                "area_um2": score["area_um2"],
                "cell_count": score.get("synth", {}).get("cell_count"),
            },
        },
    }