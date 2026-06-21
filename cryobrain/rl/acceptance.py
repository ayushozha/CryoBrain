"""Measured climb acceptance helpers (SPEC-v6.1 ambitious improvement loop)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ClimbAcceptState:
    best_suppression: float
    best_area_um2: float
    best_latency_cycles: int
    seen_hashes: set[str]

    @classmethod
    def empty(cls) -> ClimbAcceptState:
        return cls(
            best_suppression=float("-inf"),
            best_area_um2=float("inf"),
            best_latency_cycles=10**9,
            seen_hashes=set(),
        )


def _score_hw(score: dict[str, Any]) -> tuple[float, int]:
    area = float(score.get("area_um2") or score.get("synth", {}).get("area_um2") or 0.0)
    latency = int(score.get("latency_cycles") or score.get("synth", {}).get("latency_cycles") or 0)
    return area, latency


def should_accept_decoder_step(
    *,
    valid: bool,
    suppression: float,
    rtl_hash: str,
    score: dict[str, Any],
    state: ClimbAcceptState,
    history_len: int,
) -> bool:
    """Accept measured accuracy wins or strict hardware Pareto wins at tied accuracy."""
    if not valid:
        return False
    if history_len == 0:
        return True
    if rtl_hash in state.seen_hashes:
        return False

    area, latency = _score_hw(score)
    if suppression > state.best_suppression + 1e-12:
        return True

    if abs(suppression - state.best_suppression) <= 1e-12:
        if area < state.best_area_um2 - 1e-9:
            return True
        if abs(area - state.best_area_um2) <= 1e-9 and latency < state.best_latency_cycles:
            return True
    return False


def update_accept_state(
    state: ClimbAcceptState,
    *,
    suppression: float,
    rtl_hash: str,
    score: dict[str, Any],
) -> ClimbAcceptState:
    area, latency = _score_hw(score)
    return ClimbAcceptState(
        best_suppression=max(state.best_suppression, suppression),
        best_area_um2=min(state.best_area_um2, area),
        best_latency_cycles=min(state.best_latency_cycles, latency),
        seen_hashes=state.seen_hashes | {rtl_hash},
    )