"""L5 budget gate — cryo envelope on measured synth metrics (SPEC-v5 G8)."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from cryobrain.cost_model.envelope import within_envelope
from cryobrain.rtl_grader.synth_metrics import synth_metrics
from cryobrain.types import CryoBudget


class L5Result(TypedDict):
    passed: bool
    area_um2: float
    latency_cycles: int
    power_mw_est: float


def run_l5(rtl_path: Path, *, budget: CryoBudget | None = None) -> L5Result:
    metrics = synth_metrics(rtl_path)
    passed = metrics["valid"] and within_envelope(
        area_um2=metrics["area_um2"],
        latency_cycles=metrics["latency_cycles"],
        power_mw_est=metrics["power_mw_est"],
        budget=budget,
    )
    return L5Result(
        passed=passed,
        area_um2=metrics["area_um2"],
        latency_cycles=metrics["latency_cycles"],
        power_mw_est=metrics["power_mw_est"],
    )