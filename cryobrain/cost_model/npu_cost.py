"""NPU-style hardware cost model (SPEC F4)."""

from __future__ import annotations

from dataclasses import dataclass

from cryobrain.types import CryoBudget, DesignConfig


@dataclass(frozen=True)
class HardwareMetrics:
    mac_count: int
    area_mm2: float
    latency_cycles: int
    power_mw: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "mac_count": self.mac_count,
            "area_mm2": self.area_mm2,
            "latency_cycles": self.latency_cycles,
            "power_mw": self.power_mw,
        }


def estimate_hardware_metrics(
    design: DesignConfig,
    *,
    calibrated_area_per_mac: float = 1.5e-6,
) -> HardwareMetrics:
    """Estimate area/latency/power from design knobs."""
    macs_per_layer = design.window_length * (2 ** design.bitwidth)
    mac_count = macs_per_layer * design.num_layers
    weight_bits = mac_count * design.bitwidth
    area_mm2 = mac_count * design.bitwidth * calibrated_area_per_mac + weight_bits * 2e-7
    latency_cycles = max(1, design.pipeline_depth // max(design.parallelism, 1))
    # Calibrated so default starter config sits ~60% of the 8 mW Riverlane anchor.
    power_mw = 0.00488 * mac_count * design.bitwidth / max(design.parallelism, 1)
    return HardwareMetrics(
        mac_count=mac_count,
        area_mm2=area_mm2,
        latency_cycles=latency_cycles,
        power_mw=power_mw,
    )


def meets_cryo_budget(metrics: HardwareMetrics, budget: CryoBudget) -> bool:
    return (
        metrics.latency_cycles <= budget.max_latency_cycles
        and metrics.area_mm2 <= budget.max_area_mm2
        and metrics.power_mw <= budget.max_power_mw
    )


def latency_score(metrics: HardwareMetrics, budget: CryoBudget) -> float:
    if metrics.latency_cycles > budget.max_latency_cycles:
        return 0.0
    return 1.0 - (metrics.latency_cycles / budget.max_latency_cycles)


def area_score(metrics: HardwareMetrics, budget: CryoBudget) -> float:
    if metrics.area_mm2 > budget.max_area_mm2:
        return 0.0
    return 1.0 - (metrics.area_mm2 / budget.max_area_mm2)