"""Cryo budget envelope thresholds for L5 gate (not LER reward)."""

from __future__ import annotations

from cryobrain.types import CryoBudget

DEFAULT_BUDGET = CryoBudget(max_latency_cycles=64, max_area_mm2=0.06, max_power_mw=8.0)


def within_envelope(
    *,
    area_um2: float,
    latency_cycles: int,
    power_mw_est: float,
    budget: CryoBudget | None = None,
) -> bool:
    budget = budget or DEFAULT_BUDGET
    max_area_um2 = budget.max_area_mm2 * 1_000_000.0
    return (
        latency_cycles <= budget.max_latency_cycles
        and area_um2 <= max_area_um2
        and power_mw_est <= budget.max_power_mw
    )