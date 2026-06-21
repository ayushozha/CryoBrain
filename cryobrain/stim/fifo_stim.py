"""FIFO traffic stimulus + reference model (SPEC-v5 GEN / C9).

This is the FIFO analogue of the decoder's Stim error vectors: a deterministic
*traffic generator* that drives the stream-arbiter FIFO, plus a cycle-accurate
Python reference model of the GOLDEN FIFO behavior. It is FIFO traffic, NOT
quantum Stim — named ``fifo_stim`` for consistency with the env's "stim = vector
source" convention.

What it produces:
  * :func:`generate_traffic` — a deterministic per-cycle offered-load schedule
    (lane0/lane1 valid + data, and downstream ``yumi`` pop pressure). Bursty
    offered load with intermittent backpressure is what makes FIFO *depth*
    matter — a deeper FIFO drains more of the offered items in the window.
  * :class:`FifoRefModel` — the same arbitration + queue logic as the cocotb DV
    golden model (round-robin arbiter, one-spare-entry full handling). Used two
    ways: (a) by the sim DV as the bit-exact correctness oracle (L1 gate), and
    (b) here to compute the *reference drained count* a given ``depth`` achieves
    on this exact traffic — which IS the measured throughput when the RTL sim
    confirms bit-exactness.

The MEASURED metric (sustained throughput) is computed by running the GENERATED
RTL against this traffic in cocotb+Verilator and counting items actually drained
(``valid_o && yumi_i``) over the cycle window. On Windows (no Verilator) the
sim boundary is mocked in the unit test; the real measured run is WSL-only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrafficCycle:
    """One cycle of offered load + pop pressure."""

    valid0: int
    data0: int
    valid1: int
    data1: int
    yumi: int

    def to_dict(self) -> dict[str, int]:
        return {
            "valid0": self.valid0,
            "data0": self.data0,
            "valid1": self.valid1,
            "data1": self.data1,
            "yumi": self.yumi,
        }


_TRAFFIC_PERIOD = 12  # half-period of the fill/drain phase (> any small depth).


def generate_traffic(*, cycles: int = 64, width: int = 8, seed: int = 1729) -> list[TrafficCycle]:
    """Deterministic phase traffic: ingress-only bursts, then drain-only bursts.

    Alternating ``period``-cycle phases: a *fill* phase offers data on both lanes
    with no pop, then a *drain* phase pops with no ingress. Because each phase is
    longer than a small FIFO's depth, a SHALLOW FIFO backpressures mid-fill and
    permanently loses offered items, while a DEEPER FIFO buffers the whole burst
    and drains it all in the next phase — so measured throughput rises strongly
    and monotonically with ``depth`` (the GEN climb signal). ``seed`` keeps the
    schedule deterministic / reproducible across runs.
    """
    import random

    rng = random.Random(seed)  # reserved for future jitter; keeps the API stable
    mask = (1 << width) - 1
    out: list[TrafficCycle] = []
    for c in range(cycles):
        fill_phase = (c // _TRAFFIC_PERIOD) % 2 == 0
        if fill_phase:
            out.append(
                TrafficCycle(
                    valid0=1,
                    data0=(0x40 + c) & mask,
                    valid1=1,
                    data1=(0xA0 + c) & mask,
                    yumi=0,
                )
            )
        else:
            out.append(TrafficCycle(valid0=0, data0=0, valid1=0, data1=0, yumi=1))
    _ = rng  # silence unused in the current deterministic schedule
    return out


def to_vector_rows(traffic: list[TrafficCycle]) -> list[dict[str, int]]:
    """Serialize traffic to plain dict rows (for the sim DV / .mem export)."""
    return [t.to_dict() for t in traffic]


class FifoRefModel:
    """Cycle-accurate golden reference (mirrors the cocotb DV ``FifoModel``).

    Round-robin two-lane arbiter feeding a single FIFO of capacity ``depth`` with
    the one-spare-entry full allowance. ``step`` advances one cycle and returns
    whether an item was drained this cycle.
    """

    def __init__(self, depth: int) -> None:
        self.depth = depth
        self.queue: list[int] = []
        self.rr_next = 0

    def step(self, cyc: TrafficCycle) -> bool:
        """Advance one cycle on offered load ``cyc``; return True if an item drained."""
        valid = len(self.queue) != 0
        pop = bool(cyc.yumi and valid)
        can_accept = len(self.queue) < self.depth or pop
        ready0 = ready1 = 0
        if can_accept:
            if cyc.valid0 and cyc.valid1:
                ready0 = 0 if self.rr_next else 1
                ready1 = 1 if self.rr_next else 0
            elif cyc.valid0:
                ready0 = 1
            elif cyc.valid1:
                ready1 = 1
        push0 = bool(ready0 and cyc.valid0)
        push1 = bool(ready1 and cyc.valid1)

        if pop:
            self.queue.pop(0)
        if push0:
            self.queue.append(cyc.data0)
            self.rr_next = 1
        elif push1:
            self.queue.append(cyc.data1)
            self.rr_next = 0
        return pop


def reference_drained(traffic: list[TrafficCycle], *, depth: int) -> int:
    """Items the GOLDEN FIFO of capacity ``depth`` drains on this exact traffic.

    This is the correctness-anchored reference the sim must match bit-for-bit; on
    a verified RTL run the sim's drained count EQUALS this. We expose it so the
    measured-metric direction is checkable: ``reference_drained`` is monotone
    non-decreasing in ``depth`` for the bursty traffic above.
    """
    model = FifoRefModel(depth)
    return sum(1 for cyc in traffic if model.step(cyc))


def sustained_throughput(drained: int, cycles: int) -> float:
    """Measured throughput = drained items / cycles (0..1). The FIFO reward axis."""
    if cycles <= 0:
        return 0.0
    return drained / cycles
