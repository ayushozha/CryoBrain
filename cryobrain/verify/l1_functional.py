"""L1 functional gate — Verilator lint (SPEC-v5 G6)."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from cryobrain.rtl_grader.flow import run_cmd
from cryobrain.rtl_grader.stage import cleanup_stage, stage_rtl_workdir


class L1Result(TypedDict):
    passed: bool
    log_path: str


def run_l1(rtl_path: Path) -> L1Result:
    stage = stage_rtl_workdir(rtl_path, prefix="cryobrain-l1-")
    log_path = stage / "reports" / "l1_lint.log"
    try:
        rtl = stage / "rtl" / "cryo_brain_decoder.sv"
        proc = run_cmd(
            ["verilator", "--lint-only", "-Wall", "-Wno-fatal", "--top-module", "cryo_brain_decoder", str(rtl)],
            cwd=stage,
        )
        log_path.write_text(proc.stdout or "", encoding="utf-8")
        return L1Result(passed=proc.returncode == 0, log_path=str(log_path))
    finally:
        cleanup_stage(stage)