"""Measured FIFO throughput from cocotb+Verilator sim (SPEC-v5 GEN / C9).

The FIFO analogue of :func:`cryobrain.accuracy.measured_ler.measure_candidate_ler`.
It runs the GENERATED FIFO ``.sv`` against the :mod:`cryobrain.stim.fifo_stim`
traffic in a real cocotb+Verilator simulation and returns the MEASURED sustained
throughput (items actually drained / cycles) plus a correctness gate.

The metric is NOT a formula: ``throughput`` = drained items counted from the sim
run. ``valid`` is the L1 correctness gate — the sim's cycle-accurate reference
model (golden FIFO behavior) must match the DUT bit-for-bit, else throughput is
not credited (reward 0). The single-entry FIFO is the baseline anchor (the
``mwpm``-style reference), so ``suppression`` = throughput gain vs that baseline.

Linux/WSL only (Verilator). On Windows the EDA tools are absent: ``measure_fifo``
reports ``valid=False`` / throughput 0 and the GEN climb is skipped (the wsl-
marked test carries the real measured gate). No fake throughput is produced here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cryobrain.rtl_grader.flow import eda_tools_available, run_cmd
from cryobrain.stim.fifo_stim import (
    generate_traffic,
    reference_drained,
    sustained_throughput,
)

ROOT = Path(__file__).resolve().parents[2]
TASK_ROOT = ROOT / "tasks" / "async_fifo"
_BASELINE_DEPTH = 1  # single-entry FIFO = the throughput baseline anchor.


@dataclass(frozen=True)
class FifoMeasureResult:
    """Measured FIFO throughput (all fields from the sim run, no formula)."""

    throughput: float
    baseline_throughput: float
    suppression: float
    drained: int
    cycles: int
    sim_valid: bool
    rtl_path: str

    def to_score(self) -> dict[str, object]:
        """A ``score_measured``-shaped dict the FIFO step + memory consume."""
        return {
            "reward": self.throughput if self.sim_valid else 0.0,
            "valid": self.sim_valid,
            "throughput": self.throughput,
            "baseline_throughput": self.baseline_throughput,
            "suppression": self.suppression,
            "drained": self.drained,
            "cycles": self.cycles,
            "layers_passed": ["L1"] if self.sim_valid else [],
            "source": "measured-fifo-sim",
            "rtl_path": self.rtl_path,
        }


def _parse_sim_drained(stdout: str) -> tuple[int, int, bool] | None:
    """Read ``FIFO_THROUGHPUT drained=<n> cycles=<m> match=<0|1>`` from sim stdout."""
    import re

    m = re.search(
        r"FIFO_THROUGHPUT\s+drained=(?P<drained>\d+)\s+cycles=(?P<cycles>\d+)\s+match=(?P<match>[01])",
        stdout,
    )
    if not m:
        return None
    return int(m.group("drained")), int(m.group("cycles")), m.group("match") == "1"


def measure_fifo(
    rtl_path: Path,
    *,
    depth: int,
    width: int = 8,
    cycles: int = 64,
    seed: int = 1729,
    task_root: Path = TASK_ROOT,
) -> FifoMeasureResult:
    """Run ``rtl_path`` against the FIFO traffic in sim; return measured throughput.

    The baseline anchor (single-entry FIFO drained count on the SAME traffic) is
    computed from the cycle-accurate reference model so ``suppression`` is the
    measured throughput gain of this design over the minimal FIFO.
    """
    rtl_path = Path(rtl_path).resolve()
    traffic = generate_traffic(cycles=cycles, width=width, seed=seed)
    baseline_drained = reference_drained(traffic, depth=_BASELINE_DEPTH)
    baseline_tp = sustained_throughput(baseline_drained, len(traffic))

    if not eda_tools_available():
        # Windows / no Verilator: do NOT fabricate a measured number.
        return FifoMeasureResult(
            throughput=0.0,
            baseline_throughput=baseline_tp,
            suppression=0.0,
            drained=0,
            cycles=len(traffic),
            sim_valid=False,
            rtl_path=str(rtl_path),
        )

    drained, sim_cycles, match = _run_sim(rtl_path, traffic, width=width, task_root=task_root)
    throughput = sustained_throughput(drained, sim_cycles) if match else 0.0
    suppression = throughput - baseline_tp
    return FifoMeasureResult(
        throughput=throughput,
        baseline_throughput=baseline_tp,
        suppression=suppression,
        drained=drained,
        cycles=sim_cycles,
        sim_valid=match,
        rtl_path=str(rtl_path),
    )


def _run_sim(
    rtl_path: Path,
    traffic,
    *,
    width: int,
    task_root: Path,
) -> tuple[int, int, bool]:
    """Drive the cocotb throughput testbench (WSL). Returns (drained, cycles, match)."""
    from cryobrain.stim.fifo_stim import to_vector_rows

    test_module = task_root / "dv" / "cocotb" / "test_fifo_throughput.py"
    runner = task_root / "scripts" / "run_fifo_cocotb.py"
    traffic_json = rtl_path.parent / "fifo_traffic.json"
    traffic_json.write_text(json.dumps(to_vector_rows(traffic)), encoding="utf-8")
    report = rtl_path.parent / "fifo_throughput.json"

    proc = run_cmd(
        [
            "python3",
            str(runner),
            "--rtl",
            str(rtl_path),
            "--tests",
            str(test_module),
            "--traffic",
            str(traffic_json),
            "--report",
            str(report),
        ],
        cwd=rtl_path.parent,
        timeout=300,
    )
    parsed = _parse_sim_drained(proc.stdout or "")
    if parsed is not None:
        return parsed
    if report.is_file():
        data = json.loads(report.read_text(encoding="utf-8"))
        return int(data["drained"]), int(data["cycles"]), bool(data["match"])
    return 0, len(traffic), False
