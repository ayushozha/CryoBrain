"""L4 synthesis sign-off — Yosys clean synth (SPEC-v5 G7)."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from cryobrain.rtl_grader.synth_metrics import synth_metrics


class L4Result(TypedDict):
    passed: bool
    log_path: str
    cell_count: int


def run_l4(rtl_path: Path) -> L4Result:
    metrics = synth_metrics(rtl_path)
    return L4Result(
        passed=metrics["valid"],
        log_path=metrics["yosys_log_path"],
        cell_count=metrics["cell_count"],
    )