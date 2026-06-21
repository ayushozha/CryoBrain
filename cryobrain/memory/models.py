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
``decoder_quality_multiplier``. We reuse Grok's ``DesignConfig`` (dataclass)
and ``MeasureResult`` (TypedDict) shapes here rather than redefining them.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from cryobrain.accuracy.types import MeasureResult
from cryobrain.types import DesignConfig


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
    """Per-variant synthesis block (subset of Grok SynthMetrics)."""

    model_config = ConfigDict(extra="forbid")

    area_um2: float
    latency_cycles: int


class Verification(BaseModel):
    """Which verification layers (L1..L5) ran and whether the design passed."""

    model_config = ConfigDict(extra="forbid")

    layers: list[str] = Field(default_factory=list)
    passed: bool = False


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
        synth: Synth | dict[str, Any],
        verification: Verification | dict[str, Any],
        provenance: Provenance | dict[str, Any],
    ) -> "MemoryRecord":
        """Construct a record from Grok types directly (no hand-built dicts).

        ``design`` reuses ``DesignConfig.to_dict``; ``measurement`` accepts a raw
        ``MeasureResult`` and routes through ``Measurement.from_measure_result``.
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
            synth=synth if isinstance(synth, Synth) else Synth(**dict(synth)),
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
