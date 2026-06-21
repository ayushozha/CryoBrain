"""Typed results for measured accuracy (SPEC-v5 P0)."""

from __future__ import annotations

from typing import TypedDict


class MeasureResult(TypedDict):
    candidate_ler: float
    mwpm_ler: float
    suppression: float
    shots: int
    vector_source: str
    rtl_path: str
    benchmark_vectors: int
    benchmark_failures: int
    rtl_valid: bool