"""Per-variant Yosys synthesis metrics (SPEC-v5 G5 / P1)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import TypedDict

from cryobrain.rtl_grader.flow import run_cmd
from cryobrain.rtl_grader.stage import cleanup_stage, stage_rtl_workdir

_AREA_PER_CELL_UM2 = 1.5
_POWER_MW_PER_CELL = 0.012
_DEFAULT_LATENCY = 8


class SynthMetrics(TypedDict):
    area_um2: float
    latency_cycles: int
    power_mw_est: float
    valid: bool
    yosys_log_path: str
    cell_count: int


def _parse_cell_count(proc_json: Path) -> int:
    if not proc_json.is_file():
        return 0
    data = json.loads(proc_json.read_text(encoding="utf-8"))
    cells = data.get("modules", {}).get("cryo_brain_decoder", {}).get("cells", {})
    return len(cells)


def _parse_pipeline_depth(rtl_text: str) -> int:
    match = re.search(r"parameter\s+int\s+PIPELINE_DEPTH\s*=\s*(\d+)", rtl_text)
    if match:
        return max(1, int(match.group(1)))
    match = re.search(r"parameter\s+int\s+NUM_LAYERS\s*=\s*(\d+)", rtl_text)
    if match:
        return max(1, int(match.group(1)) * 2)
    return _DEFAULT_LATENCY


def _parse_parallelism(rtl_text: str) -> int:
    match = re.search(r"parameter\s+int\s+PARALLELISM\s*=\s*(\d+)", rtl_text)
    return max(1, int(match.group(1))) if match else 1


def synth_metrics(rtl_path: Path) -> SynthMetrics:
    """Run Yosys on ``rtl_path`` and return measured synthesis metrics."""
    rtl_path = rtl_path.resolve()
    rtl_text = rtl_path.read_text(encoding="utf-8")
    stage = stage_rtl_workdir(rtl_path, prefix="cryobrain-synth-")
    log_path = stage / "reports" / "yosys_synth.log"
    try:
        synth_script = stage / "synth" / "synth.ys"
        if not synth_script.is_file():
            log_path.write_text("missing synth/synth.ys\n", encoding="utf-8")
            return SynthMetrics(
                area_um2=0.0,
                latency_cycles=_parse_pipeline_depth(rtl_text),
                power_mw_est=0.0,
                valid=False,
                yosys_log_path=str(log_path),
                cell_count=0,
            )

        proc = run_cmd(["yosys", "-q", "-s", str(synth_script)], cwd=stage, timeout=180)
        log_path.write_text(proc.stdout or "", encoding="utf-8")
        proc_json = stage / "reports" / "proc.json"
        cell_count = _parse_cell_count(proc_json)
        pipeline = _parse_pipeline_depth(rtl_text)
        parallel = _parse_parallelism(rtl_text)
        latency = max(1, pipeline // parallel + pipeline % parallel)
        area_um2 = cell_count * _AREA_PER_CELL_UM2
        power_mw_est = cell_count * _POWER_MW_PER_CELL
        has_latch = "latch" in (proc.stdout or "").lower() and "no latch" not in (proc.stdout or "").lower()
        valid = proc.returncode == 0 and proc_json.is_file() and cell_count > 0 and not has_latch

        persist_log = rtl_path.with_suffix(".yosys.log")
        shutil.copy2(log_path, persist_log)

        return SynthMetrics(
            area_um2=area_um2,
            latency_cycles=latency,
            power_mw_est=power_mw_est,
            valid=valid,
            yosys_log_path=str(persist_log),
            cell_count=cell_count,
        )
    finally:
        cleanup_stage(stage)