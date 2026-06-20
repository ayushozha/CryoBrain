from cryobrain.cost_model.npu_cost import HardwareMetrics, estimate_hardware_metrics
from cryobrain.reward.compute_reward import compute_reward
from cryobrain.types import CryoBudget, DesignConfig


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