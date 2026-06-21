"""Typed models for the measured-variant memory record (SPEC-v5 C1).

The frozen record schema (HANDOFF-CLAUDE.md "Memory Record Schema") is::

    {
      "rtl_path": "...",
      "design": { ...DesignConfig... },
      "measurement": { "candidate_ler", "mwpm_ler", "suppression" },
      "synth": { "area_um2", "latency_cycles" },
      "verification": { "layers": [...], "passed": bool },
      "provenance": { "step", "backend" }
    }

The ``measurement`` block is sourced from ``measure_candidate_ler``
(a ``MeasureResult``) ONLY — no formula/proxy LER, no
``decoder_quality_multiplier``. The ``synth`` block stores the subset of
Grok's ``synth_metrics`` output that matters for pareto/budget reasoning. We
reuse Grok's ``DesignConfig`` (dataclass), ``MeasureResult`` and
``SynthMetrics`` (TypedDicts) shapes here rather than redefining them.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from cryobrain.accuracy.types import MeasureResult
from cryobrain.rtl_grader.synth_metrics import SynthMetrics
from cryobrain.types import DesignConfig

# The real verification layers in cryobrain/verify/ (run_l1, run_l4, run_l5).
# There is no L2/L3 gate in-tree; records must reflect what actually ran.
VERIFY_LAYERS: tuple[str, ...] = ("L1", "L4", "L5")


class Measurement(BaseModel):
    """Measured-accuracy block — candidate_ler MUST come from a MeasureResult."""

    model_config = ConfigDict(extra="forbid")

    candidate_ler: float
    mwpm_ler: float
    suppression: float

    @classmethod
    def from_measure_result(cls, result: MeasureResult | dict[str, Any]) -> "Measurement":
        """Adapt a Grok ``measure_candidate_ler`` output into the stored block.

        Pulls measured fields only; never a proxy. Accepts the ``MeasureResult``
        TypedDict (a plain dict at runtime) so callers pass the API output verbatim.
        """
        return cls(
            candidate_ler=float(result["candidate_ler"]),
            mwpm_ler=float(result["mwpm_ler"]),
            suppression=float(result["suppression"]),
        )


class Synth(BaseModel):
    """Per-variant synthesis block — subset of Grok ``SynthMetrics``.

    We persist the measured fields that matter for pareto / budget reasoning
    (area, latency, estimated power, synth validity) and deliberately DROP the
    raw ``yosys_log_path`` (machine-local path, churns per run) and
    ``cell_count`` (intermediate Yosys detail) so the record stays clean and
    portable. ``extra="forbid"`` still guards the block.
    """

    model_config = ConfigDict(extra="forbid")

    area_um2: float
    latency_cycles: int
    power_mw_est: float = 0.0
    valid: bool = True

    @classmethod
    def from_synth_metrics(cls, metrics: SynthMetrics | dict[str, Any]) -> "Synth":
        """Adapt a Grok ``synth_metrics`` output into the stored block.

        Selects the persisted subset only — mirrors ``Measurement.from_measure_result``.
        Drops ``yosys_log_path`` and ``cell_count``; never dumps the whole dict.
        ``area_um2``/``latency_cycles`` are required; ``power_mw_est``/``valid``
        fall back to the model defaults if a caller passes only the core pair.
        """
        return cls(
            area_um2=float(metrics["area_um2"]),
            latency_cycles=int(metrics["latency_cycles"]),
            power_mw_est=float(metrics.get("power_mw_est", 0.0)),
            valid=bool(metrics.get("valid", True)),
        )


class Verification(BaseModel):
    """Which verification layers ran (real set: L1, L4, L5) and whether passed.

    The in-tree gates are ``run_l1`` (Verilator lint), ``run_l4`` (Yosys synth
    sign-off), and ``run_l5`` (cryo budget) — see :data:`VERIFY_LAYERS`. There
    is no L2/L3 layer, so records should not invent one.
    """

    model_config = ConfigDict(extra="forbid")

    layers: list[str] = Field(default_factory=list)
    passed: bool = False

    @classmethod
    def from_layers(cls, layers: list[str] | None = None, *, passed: bool = False) -> "Verification":
        """Build a verification block, defaulting to the real :data:`VERIFY_LAYERS`."""
        return cls(layers=list(layers) if layers is not None else list(VERIFY_LAYERS), passed=passed)


class Provenance(BaseModel):
    """Where this record came from in the measured loop."""

    model_config = ConfigDict(extra="forbid")

    step: int
    backend: str = "verilator+stim+yosys"


class MemoryRecord(BaseModel):
    """One measured, verified decoder variant — the unit C5 writes, C10 reads."""

    model_config = ConfigDict(extra="forbid")

    rtl_path: str
    design: dict[str, int]
    measurement: Measurement
    synth: Synth
    verification: Verification
    provenance: Provenance

    @classmethod
    def build(
        cls,
        *,
        rtl_path: str,
        design: DesignConfig | dict[str, Any],
        measurement: MeasureResult | Measurement | dict[str, Any],
        synth: SynthMetrics | Synth | dict[str, Any],
        verification: Verification | dict[str, Any],
        provenance: Provenance | dict[str, Any],
    ) -> "MemoryRecord":
        """Construct a record from Grok types directly (no hand-built dicts).

        ``design`` reuses ``DesignConfig.to_dict``; ``measurement`` accepts a raw
        ``MeasureResult`` (routed via ``Measurement.from_measure_result``); ``synth``
        accepts a raw ``synth_metrics`` output (routed via ``Synth.from_synth_metrics``,
        which selects the stored subset and drops log path / cell_count).
        """
        design_dict = design.to_dict() if isinstance(design, DesignConfig) else dict(design)
        if isinstance(measurement, Measurement):
            meas = measurement
        else:
            meas = Measurement.from_measure_result(measurement)
        return cls(
            rtl_path=rtl_path,
            design=design_dict,
            measurement=meas,
            synth=synth if isinstance(synth, Synth) else Synth.from_synth_metrics(synth),
            verification=(
                verification
                if isinstance(verification, Verification)
                else Verification(**dict(verification))
            ),
            provenance=(
                provenance
                if isinstance(provenance, Provenance)
                else Provenance(**dict(provenance))
            ),
        )
