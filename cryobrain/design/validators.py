"""Validate DesignConfig search space (SPEC-v5 G9)."""

from __future__ import annotations

from cryobrain.types import DesignConfig

_ALLOWED_BITWIDTH = frozenset({2, 4, 8})
_ALLOWED_PARALLELISM = frozenset({1, 2, 4})


def validate_design(design: DesignConfig) -> None:
    if design.bitwidth not in _ALLOWED_BITWIDTH:
        raise ValueError(f"bitwidth must be one of {sorted(_ALLOWED_BITWIDTH)}")
    if not 1 <= design.num_layers <= 8:
        raise ValueError("num_layers must be in [1, 8]")
    if design.parallelism not in _ALLOWED_PARALLELISM:
        raise ValueError(f"parallelism must be one of {sorted(_ALLOWED_PARALLELISM)}")
    if not 1 <= design.pipeline_depth <= 16:
        raise ValueError("pipeline_depth must be in [1, 16]")
    if not 4 <= design.window_length <= 32:
        raise ValueError("window_length must be in [4, 32]")