"""FIFO design config (SPEC-v5 GEN / C9) — the FIFO sibling of ``DesignConfig``.

The decoder's :class:`cryobrain.types.DesignConfig` describes a QEC decoder
(num_layers, window_length, parallelism, ...). None of those knobs map onto a
stream-arbiter FIFO, so the FIFO target defines its own small, frozen config —
the same pattern, a different domain. Kept deliberately tiny
(minimal-code-dependency-first): two real knobs the measured throughput metric
responds to.

  * ``depth``  — FIFO capacity (entries). Deeper FIFO absorbs more burst before
    backpressuring, so it sustains higher measured throughput under bursty
    traffic. This is the primary optimization knob.
  * ``width``  — datapath bit-width. Affects area/correctness vectors, not the
    capacity story; varied so distinct configs yield distinct ``.sv`` and area.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, replace

_DEPTH_CHOICES = (2, 4, 8, 16, 32)
_WIDTH_CHOICES = (8, 16, 32)


@dataclass(frozen=True)
class FifoConfig:
    depth: int = 4
    width: int = 8

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "FifoConfig":
        return cls(
            depth=int(data.get("depth", 4)),
            width=int(data.get("width", 8)),
        )


def validate_fifo(design: FifoConfig) -> None:
    """Reject configs that would generate invalid/non-synthesizable RTL.

    ``$clog2(depth)`` addressing needs depth >= 2; width must be a positive
    datapath. Mirrors ``cryobrain.design.validators.validate_design`` in spirit.
    """
    if design.depth < 2:
        raise ValueError(f"fifo depth must be >= 2 (got {design.depth})")
    if design.width < 1:
        raise ValueError(f"fifo width must be >= 1 (got {design.width})")


def fifo_preset_variants() -> list[FifoConfig]:
    """Three distinct configs (distinct ``.sv``) — GEN's MP1-style spread.

    Ordered shallow -> deep so a depth-greedy proposer has a clear measured climb.
    """
    return [
        FifoConfig(depth=2, width=8),
        FifoConfig(depth=8, width=8),
        FifoConfig(depth=16, width=16),
    ]


def mutate_fifo(design: FifoConfig, rng: random.Random | None = None) -> FifoConfig:
    """Mutate one knob. Biased toward deeper FIFOs (the throughput direction)."""
    rng = rng or random.Random()
    if rng.random() < 0.7:
        deeper = [d for d in _DEPTH_CHOICES if d > design.depth] or [design.depth]
        return replace(design, depth=min(deeper))
    return replace(design, width=rng.choice(_WIDTH_CHOICES))
