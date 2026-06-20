"""Verifiable reward with validity gate (SPEC §4)."""

from __future__ import annotations

from dataclasses import dataclass

from cryobrain.cost_model.npu_cost import (
    HardwareMetrics,
    area_score,
    latency_score,
    meets_cryo_budget,
)
from cryobrain.types import CryoBudget


@dataclass(frozen=True)
class RewardBreakdown:
    reward: float
    rtl_valid: bool
    meets_budget: bool
    ler_suppression_vs_mwpm: float
    latency_component: float
    area_component: float
    hard_caps: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "reward": self.reward,
            "rtl_valid": self.rtl_valid,
            "meets_budget": self.meets_budget,
            "ler_suppression_vs_mwpm": self.ler_suppression_vs_mwpm,
            "latency_component": self.latency_component,
            "area_component": self.area_component,
            "hard_caps": self.hard_caps,
        }


def ler_suppression_vs_mwpm(candidate_ler: float, mwpm_ler: float) -> float:
    """Continuous decode-quality term: how much better than MWPM (bounded 0–1)."""
    if mwpm_ler <= 0:
        return 0.0
    ratio = candidate_ler / mwpm_ler
    return max(0.0, min(1.0, 1.0 - ratio))


def compute_reward(
    *,
    rtl_valid: bool,
    metrics: HardwareMetrics,
    budget: CryoBudget,
    candidate_ler: float,
    mwpm_ler: float,
    w_acc: float = 0.7,
    w_lat: float = 0.15,
    w_area: float = 0.15,
) -> RewardBreakdown:
    hard_caps: list[str] = []
    if not rtl_valid:
        hard_caps.append("rtl_invalid")
        return RewardBreakdown(
            reward=0.0,
            rtl_valid=False,
            meets_budget=False,
            ler_suppression_vs_mwpm=0.0,
            latency_component=0.0,
            area_component=0.0,
            hard_caps=hard_caps,
        )

    budget_ok = meets_cryo_budget(metrics, budget)
    if not budget_ok:
        hard_caps.append("cryo_budget_exceeded")
        return RewardBreakdown(
            reward=0.0,
            rtl_valid=True,
            meets_budget=False,
            ler_suppression_vs_mwpm=0.0,
            latency_component=0.0,
            area_component=0.0,
            hard_caps=hard_caps,
        )

    acc = ler_suppression_vs_mwpm(candidate_ler, mwpm_ler)
    lat = latency_score(metrics, budget)
    area = area_score(metrics, budget)
    reward = w_acc * acc + w_lat * lat + w_area * area
    return RewardBreakdown(
        reward=max(0.0, min(1.0, reward)),
        rtl_valid=True,
        meets_budget=True,
        ler_suppression_vs_mwpm=acc,
        latency_component=lat,
        area_component=area,
        hard_caps=hard_caps,
    )