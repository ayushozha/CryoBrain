"""Cocotb throughput DV for the parametric stream-arbiter FIFO (SPEC-v5 GEN).

Drives the GENERATED FIFO with deterministic traffic (from a JSON file written
by ``cryobrain.stim.fifo_stim``), counts items actually drained (``valid_o &&
yumi_i``), and checks the DUT bit-for-bit against the cycle-accurate golden
reference model. Emits a single machine-readable line the measure layer parses:

    FIFO_THROUGHPUT drained=<n> cycles=<m> match=<0|1>

``match`` is the L1 correctness gate: if the DUT ever disagrees with the
reference (wrong ready/valid/data/count), match=0 and throughput is not credited.
``drained`` / ``cycles`` give the MEASURED sustained throughput (drained/cycles).
"""

import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


def _traffic_path() -> Path:
    raw = os.environ.get("FIFO_TRAFFIC_FILE")
    if not raw:
        raise RuntimeError("FIFO_TRAFFIC_FILE not set")
    return Path(raw)


def _report_path() -> Path | None:
    raw = os.environ.get("FIFO_REPORT_FILE")
    return Path(raw) if raw else None


def as_int(value) -> int:
    return int(value)


class RefModel:
    """Cycle-accurate golden reference (same logic as the generated FIFO)."""

    def __init__(self, depth: int) -> None:
        self.depth = depth
        self.queue: list[int] = []
        self.rr_next = 0

    def comb(self, v0, d0, v1, d1, y):
        valid = len(self.queue) != 0
        pop = bool(y and valid)
        can_accept = len(self.queue) < self.depth or pop
        ready0 = ready1 = selected = 0
        if can_accept:
            if v0 and v1:
                ready0 = 0 if self.rr_next else 1
                ready1 = 1 if self.rr_next else 0
                selected = self.rr_next
            elif v0:
                ready0 = 1
            elif v1:
                ready1 = 1
                selected = 1
        push0 = bool(ready0 and v0)
        push1 = bool(ready1 and v1)
        return valid, pop, ready0, ready1, selected, push0, push1

    def apply(self, pop, push0, d0, push1, d1):
        if pop:
            self.queue.pop(0)
        if push0:
            self.queue.append(d0)
            self.rr_next = 1
        elif push1:
            self.queue.append(d1)
            self.rr_next = 0


@cocotb.test()
async def measure_fifo_throughput(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, unit="ns").start())
    traffic = json.loads(_traffic_path().read_text(encoding="utf-8"))
    depth = int(os.environ.get("FIFO_DEPTH", "0")) or int(dut.depth_p.value)
    model = RefModel(depth)

    # Reset
    dut.reset_i.value = 1
    dut.valid0_i.value = 0
    dut.valid1_i.value = 0
    dut.yumi_i.value = 0
    dut.data0_i.value = 0
    dut.data1_i.value = 0
    await RisingEdge(dut.clk_i)
    await RisingEdge(dut.clk_i)
    dut.reset_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")

    drained = 0
    match = True
    cycles = 0
    for row in traffic:
        v0, d0 = row["valid0"], row["data0"]
        v1, d1 = row["valid1"], row["data1"]
        y = row["yumi"]
        dut.valid0_i.value = v0
        dut.data0_i.value = d0
        dut.valid1_i.value = v1
        dut.data1_i.value = d1
        dut.yumi_i.value = y
        await Timer(1, unit="ns")

        valid, pop, ready0, ready1, selected, push0, push1 = model.comb(v0, d0, v1, d1, y)
        if (
            as_int(dut.valid_o.value) != int(valid)
            or as_int(dut.ready0_o.value) != ready0
            or as_int(dut.ready1_o.value) != ready1
            or as_int(dut.count_o.value) != len(model.queue)
            or as_int(dut.selected_lane_o.value) != selected
        ):
            match = False
        if valid and as_int(dut.data_o.value) != model.queue[0]:
            match = False

        if pop:
            drained += 1
        cycles += 1
        await RisingEdge(dut.clk_i)
        model.apply(pop, push0, d0, push1, d1)
        await Timer(1, unit="ns")

    print(f"FIFO_THROUGHPUT drained={drained} cycles={cycles} match={1 if match else 0}")
    report = _report_path()
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps({"drained": drained, "cycles": cycles, "match": match}),
            encoding="utf-8",
        )
    assert match, "DUT diverged from golden reference (L1 correctness gate)"
