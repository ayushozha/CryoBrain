from cryobrain.cost_model.npu_cost import HardwareMetrics, estimate_hardware_metrics, meets_cryo_budget
from cryobrain.reward.compute_reward import (
    compute_reward,
    compute_reward_from_scenario,
    ler_suppression_vs_mwpm,
)
from cryobrain.types import CryoBudget, DesignConfig, ScenarioConfig


def test_validity_gate_zeros_reward():
    metrics = estimate_hardware_metrics(DesignConfig())
    budget = CryoBudget()
    result = compute_reward(
        rtl_valid=False,
        metrics=metrics,
        budget=budget,
        candidate_ler=0.01,
        mwpm_ler=0.02,
    )
    assert result.reward == 0.0
    assert "rtl_invalid" in result.hard_caps


def test_budget_gate_zeros_reward():
    metrics = HardwareMetrics(mac_count=64, area_mm2=0.08, latency_cycles=32, power_mw=4.0)
    budget = CryoBudget()
    result = compute_reward(
        rtl_valid=True,
        metrics=metrics,
        budget=budget,
        candidate_ler=0.008,
        mwpm_ler=0.02,
    )
    assert result.reward == 0.0
    assert "cryo_budget_exceeded" in result.hard_caps


def test_continuous_reward_in_band():
    metrics = HardwareMetrics(mac_count=64, area_mm2=0.04, latency_cycles=32, power_mw=4.0)
    budget = CryoBudget()
    result = compute_reward(
        rtl_valid=True,
        metrics=metrics,
        budget=budget,
        candidate_ler=0.008,
        mwpm_ler=0.02,
    )
    assert 0.2 <= result.reward <= 0.9
    assert result.ler_suppression_vs_mwpm == ler_suppression_vs_mwpm(0.008, 0.02)


def test_starter_design_meets_cryo_budget():
    design = DesignConfig()
    metrics = estimate_hardware_metrics(design)
    budget = CryoBudget()
    assert meets_cryo_budget(metrics, budget)


def test_starter_reward_lands_in_cp3_band():
    """Without measured RTL scoring, starter accuracy fails closed at MWPM parity."""
    design = DesignConfig()
    scenario = ScenarioConfig(distance=3, noise_rate=0.008, shots=200, rounds=3)
    budget = CryoBudget()
    breakdown, accuracy = compute_reward_from_scenario(
        rtl_valid=True,
        design=design,
        scenario=scenario,
        budget=budget,
        latency_cycles=12,
    )
    assert breakdown.meets_budget
    assert 0.20 <= breakdown.reward <= 0.55
    assert accuracy["mwpm_ler"] > 0.0
    assert accuracy["candidate_ler"] == accuracy["mwpm_ler"]
    assert breakdown.ler_suppression_vs_mwpm == 0.0


def test_measured_ler_changes_reward():
    """Accuracy term moves only when measured candidate LER changes."""
    budget = CryoBudget()
    metrics = HardwareMetrics(mac_count=128, area_mm2=0.03, latency_cycles=16, power_mw=4.0)
    mwpm_ler = 0.04

    worse_breakdown = compute_reward(
        rtl_valid=True,
        metrics=metrics,
        budget=budget,
        candidate_ler=0.035,
        mwpm_ler=mwpm_ler,
    )
    better_breakdown = compute_reward(
        rtl_valid=True,
        metrics=metrics,
        budget=budget,
        candidate_ler=0.02,
        mwpm_ler=mwpm_ler,
    )
    assert better_breakdown.ler_suppression_vs_mwpm > worse_breakdown.ler_suppression_vs_mwpm
    assert better_breakdown.reward > worse_breakdown.reward


def test_large_design_can_exceed_cryo_budget():
    design = DesignConfig(bitwidth=8, num_layers=4, window_length=16, parallelism=2)
    metrics = estimate_hardware_metrics(design)
    assert not meets_cryo_budget(metrics, CryoBudget())
