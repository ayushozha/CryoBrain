"""CP5 real artifacts: golden Yosys synth + Verilator trace waveform."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from cryobrain.calibration.cp3 import stage_workdir
from cryobrain.rtl_grader.flow import run_rtl_flow, run_rtl_trace


@dataclass(frozen=True)
class Cp5Result:
    synth_passed: bool
    cell_count: int
    latch_count: int
    trace_passed: bool
    vcd_path: Path | None
    syndrome_to_correction: bool
    ok: bool
    details: dict[str, object]


def _latch_count(proc_json: Path) -> int:
    if not proc_json.is_file():
        return -1
    data = json.loads(proc_json.read_text(encoding="utf-8"))
    count = 0
    for module in data.get("modules", {}).values():
        for cell in module.get("cells", {}).values():
            if cell.get("type") == "$dlatch":
                count += 1
    return count


def _parse_vcd_signals(vcd_text: str) -> dict[str, str]:
    """Map hierarchical signal suffix to VCD identifier."""
    mapping: dict[str, str] = {}
    for line in vcd_text.splitlines():
        match = re.match(r"\$var\s+\S+\s+\d+\s+(\S+)\s+(.+?)\s+\$end", line.strip())
        if not match:
            continue
        ident, name = match.group(1), match.group(2).strip()
        for key in ("syndromes_valid", "corrections_valid"):
            if name.endswith(key) or name == key:
                mapping[key] = ident
    return mapping


def assert_syndrome_to_correction(vcd_path: Path) -> bool:
    """True when corrections_valid rises after syndromes_valid in the trace."""
    if not vcd_path.is_file():
        return False
    text = vcd_path.read_text(encoding="utf-8", errors="replace")
    signals = _parse_vcd_signals(text)
    if "syndromes_valid" not in signals or "corrections_valid" not in signals:
        return False

    synd_id = signals["syndromes_valid"]
    corr_id = signals["corrections_valid"]
    values: dict[str, str] = {}
    saw_syndrome = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("$") or line.startswith("#"):
            if line.startswith("#"):
                # Value updates may follow on subsequent lines; handled below.
                pass
            continue
        if len(line) >= 2 and line[0] in "01xXzZ":
            val, ident = line[0], line[1:]
            values[ident] = val
            if ident == synd_id and val == "1":
                saw_syndrome = True
            if saw_syndrome and ident == corr_id and val == "1":
                return True
        elif len(line) >= 1 and line[0] in "bB":
            parts = line.split()
            if len(parts) == 2:
                val, ident = parts[0], parts[1]
                bit = val[-1] if val else "0"
                values[ident] = bit
                if ident == synd_id and bit == "1":
                    saw_syndrome = True
                if saw_syndrome and ident == corr_id and bit == "1":
                    return True
    return False


def run_cp5_artifacts(
    task_root: Path,
    hidden_root: Path,
    *,
    artifacts_dir: Path | None = None,
) -> Cp5Result:
    """Run golden RTL through synth + traced sim; write VCD under artifacts/."""
    scenario = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    design = json.loads((task_root / "design_config.json").read_text(encoding="utf-8"))
    workdir = stage_workdir(task_root, scenario=scenario, design=design)
    golden = hidden_root / "cryo_brain_decoder_golden.sv"
    shutil.copy2(golden, workdir / "rtl" / "cryo_brain_decoder.sv")

    rtl = run_rtl_flow(workdir, golden_mode=True)
    proc_json = workdir / "reports" / "proc.json"
    latches = _latch_count(proc_json)

    out_dir = artifacts_dir or (task_root.parents[1] / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    trace = run_rtl_trace(workdir, vcd_output=out_dir / "cryo_golden_trace.vcd")

    syndrome_ok = assert_syndrome_to_correction(trace.vcd_path) if trace.vcd_path else False
    ok = (
        rtl.synth_passed
        and rtl.lint_passed
        and rtl.cell_count > 0
        and latches == 0
        and trace.trace_passed
        and trace.vcd_path is not None
        and syndrome_ok
    )
    return Cp5Result(
        synth_passed=rtl.synth_passed and rtl.lint_passed,
        cell_count=rtl.cell_count,
        latch_count=latches,
        trace_passed=trace.trace_passed,
        vcd_path=trace.vcd_path,
        syndrome_to_correction=syndrome_ok,
        ok=ok,
        details={
            "sim_passed": rtl.sim_passed,
            "area_estimate": rtl.area_estimate,
            "benchmark_exactness": rtl.benchmark_exactness,
            "trace_logs": trace.logs,
        },
    )


def assess_cp5(result: Cp5Result) -> dict[str, object]:
    reasons: list[str] = []
    if not result.synth_passed:
        reasons.append("synth_or_lint_failed")
    if result.cell_count <= 0:
        reasons.append("zero_cell_count")
    if result.latch_count != 0:
        reasons.append("latches_detected")
    if not result.trace_passed:
        reasons.append("trace_sim_failed")
    if result.vcd_path is None or not result.vcd_path.is_file():
        reasons.append("missing_vcd")
    if not result.syndrome_to_correction:
        reasons.append("no_syndrome_to_correction_in_waveform")
    return {
        "ok": result.ok and not reasons,
        "reasons": reasons,
        "cell_count": result.cell_count,
        "latch_count": result.latch_count,
        "vcd_path": str(result.vcd_path) if result.vcd_path else None,
        "syndrome_to_correction": result.syndrome_to_correction,
    }