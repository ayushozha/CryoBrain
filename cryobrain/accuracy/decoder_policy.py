"""Simulated neural-decoder policy from design knobs (SPEC F3).

Maps ``DesignConfig`` to a candidate logical error rate relative to the MWPM
anchor.  Real Stim+PyMatching still produces ``mwpm_ler``; this hook models how
architecture choices would shift decode quality before a trained net exists.
"""

from __future__ import annotations

from cryobrain.types import DesignConfig

# Calibrated so default starter knobs land ~18% LER suppression vs MWPM (0.82×).
_STARTER_LER_MULTIPLIER = 0.82
_INVALID_RTL_LER_MULTIPLIER = 1.25


def _raw_quality_multiplier(design: DesignConfig) -> float:
    """Relative decode quality; lower multiplier ⇒ better decoder (lower LER)."""
    if design.bitwidth <= 2:
        bitwidth = 1.14
    elif design.bitwidth <= 4:
        bitwidth = 1.0
    else:
        bitwidth = max(0.70, 0.96 - 0.035 * (design.bitwidth - 4))

    layers = max(0.72, 1.06 - 0.055 * (design.num_layers - 1))
    window = max(0.82, 1.03 - 0.012 * (design.window_length - 4))
    # More parallelism slightly helps effective throughput / context reuse.
    parallel = 1.0 + 0.035 * max(0, 4 - design.parallelism)
    # Deeper pipelines add latency pressure that hurts sliding-window coverage.
    pipeline = 1.0 + 0.018 * max(0, design.pipeline_depth - 4)

    return bitwidth * layers * window * parallel * pipeline


def _starter_baseline() -> float:
    return _raw_quality_multiplier(DesignConfig())


def decoder_quality_multiplier(design: DesignConfig) -> float:
    """LER ratio vs MWPM for a valid RTL design (1.0 == MWPM parity)."""
    baseline = _starter_baseline()
    if baseline <= 0:
        return _STARTER_LER_MULTIPLIER
    scale = _STARTER_LER_MULTIPLIER / baseline
    return _raw_quality_multiplier(design) * scale


def simulate_candidate_ler(
    design: DesignConfig,
    mwpm_ler: float,
    *,
    rtl_valid: bool = True,
) -> float:
    """Map design knobs (+ validity) to a simulated candidate LER."""
    if mwpm_ler < 0:
        raise ValueError("mwpm_ler must be non-negative")
    if not rtl_valid:
        return mwpm_ler * _INVALID_RTL_LER_MULTIPLIER
    return mwpm_ler * decoder_quality_multiplier(design)