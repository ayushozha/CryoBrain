"""Golden-fixture round-trip for the C1 measured-variant store (SPEC-v5).

No EDA: a golden ``MeasureResult`` fixture stands in for ``measure_candidate_ler``
output. The holdout / pareto LER column must come from the measured
``candidate_ler`` only — never a proxy / ``decoder_quality_multiplier``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cryobrain.accuracy.types import MeasureResult
from cryobrain.memory.models import VERIFY_LAYERS, MemoryRecord, Synth, Verification
from cryobrain.memory.store import MemoryStore, rtl_hash
from cryobrain.rtl_grader.synth_metrics import SynthMetrics
from cryobrain.types import DesignConfig


def _golden_measure_result(rtl_path: Path) -> MeasureResult:
    """Stand-in for measure_candidate_ler output (shape from accuracy.types)."""
    return MeasureResult(
        candidate_ler=0.017,
        mwpm_ler=0.022,
        suppression=0.23,
        shots=1000,
        vector_source="Stim surface_code benchmark vectors",
        rtl_path=str(rtl_path),
        benchmark_vectors=64,
        benchmark_failures=1,
        rtl_valid=True,
    )


def _golden_synth_metrics(rtl_path: Path) -> SynthMetrics:
    """Stand-in for synth_metrics output (REAL shape from rtl_grader.synth_metrics).

    Carries the full TypedDict including the fields the record deliberately
    drops (``yosys_log_path``, ``cell_count``) so tests prove they are stripped.
    """
    return SynthMetrics(
        area_um2=6.1,
        latency_cycles=8,
        power_mw_est=0.048,
        valid=True,
        yosys_log_path=str(rtl_path.with_suffix(".yosys.log")),
        cell_count=4,
    )


def _make_rtl(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(f"module {name}; // {body}\nendmodule\n", encoding="utf-8")
    return p


def _golden_record(rtl_path: Path, *, step: int = 12) -> MemoryRecord:
    return MemoryRecord.build(
        rtl_path=str(rtl_path),
        design=DesignConfig(bitwidth=8, num_layers=4, parallelism=2, pipeline_depth=4, window_length=16),
        measurement=_golden_measure_result(rtl_path),
        # Real synth_metrics shape, adapted in via Synth.from_synth_metrics.
        synth=_golden_synth_metrics(rtl_path),
        # Real verify layers (L1/L4/L5) — no fictional L2/L3.
        verification=Verification.from_layers(list(VERIFY_LAYERS), passed=True),
        provenance={"step": step, "backend": "verilator+stim+yosys"},
    )


def test_round_trip_all_fields_survive(tmp_path: Path):
    """Write a record, read it back from a fresh store, assert every field survives."""
    rtl = _make_rtl(tmp_path, "step_012_parallel.sv", "golden")
    store_path = tmp_path / "measured_variants.jsonl"

    record = _golden_record(rtl)
    key = MemoryStore(store_path).record_variant(record)

    # Key is the sha256 of the RTL file contents (dedupe/provenance).
    assert key == rtl_hash(rtl)

    # Re-open from disk: nothing held in memory carries over.
    reloaded = MemoryStore(store_path)
    assert len(reloaded) == 1
    back = reloaded.all_records()[0]

    assert back.model_dump() == record.model_dump()
    assert back.rtl_path == str(rtl)
    assert back.design == {
        "bitwidth": 8,
        "num_layers": 4,
        "parallelism": 2,
        "pipeline_depth": 4,
        "window_length": 16,
    }
    assert back.measurement.mwpm_ler == 0.022
    assert back.measurement.suppression == 0.23
    assert back.synth.area_um2 == 6.1
    assert back.synth.latency_cycles == 8
    assert back.synth.power_mw_est == 0.048
    assert back.synth.valid is True
    assert back.verification.layers == ["L1", "L4", "L5"]
    assert back.verification.passed is True
    assert back.provenance.step == 12
    assert back.provenance.backend == "verilator+stim+yosys"


def test_holdout_ler_sourced_from_measured_candidate_ler(tmp_path: Path):
    """The holdout LER column must equal the measured candidate_ler, not a proxy."""
    rtl = _make_rtl(tmp_path, "step_012_parallel.sv", "golden")
    store_path = tmp_path / "measured_variants.jsonl"
    golden = _golden_measure_result(rtl)

    store = MemoryStore(store_path)
    store.record_variant(_golden_record(rtl))

    best = store.best_holdout()
    assert best is not None
    assert best.measurement.candidate_ler == golden["candidate_ler"] == 0.017


def test_best_holdout_picks_lowest_ler_among_verified(tmp_path: Path):
    store_path = tmp_path / "measured_variants.jsonl"
    store = MemoryStore(store_path)

    # Lowest LER but NOT verified -> ineligible.
    rtl_unverified = _make_rtl(tmp_path, "unverified.sv", "a")
    rec_unverified = _golden_record(rtl_unverified, step=1)
    rec_unverified.measurement.candidate_ler = 0.005
    rec_unverified.verification = Verification(layers=["L1"], passed=False)
    store.record_variant(rec_unverified)

    # Higher LER, verified.
    rtl_hi = _make_rtl(tmp_path, "verified_hi.sv", "b")
    rec_hi = _golden_record(rtl_hi, step=2)
    rec_hi.measurement.candidate_ler = 0.030
    store.record_variant(rec_hi)

    # Lower LER, verified -> should win.
    rtl_lo = _make_rtl(tmp_path, "verified_lo.sv", "c")
    rec_lo = _golden_record(rtl_lo, step=3)
    rec_lo.measurement.candidate_ler = 0.012
    store.record_variant(rec_lo)

    best = store.best_holdout()
    assert best is not None
    assert best.measurement.candidate_ler == 0.012
    assert best.verification.passed is True


def test_pareto_candidates_carry_required_fields(tmp_path: Path):
    store_path = tmp_path / "measured_variants.jsonl"
    store = MemoryStore(store_path)
    rtl = _make_rtl(tmp_path, "step_012_parallel.sv", "golden")
    store.record_variant(_golden_record(rtl))

    candidates = store.query_pareto_candidates()
    assert len(candidates) == 1
    c = candidates[0]
    assert set(c) == {"rtl_hash", "rtl_path", "ler", "area_um2", "latency_cycles"}
    assert c["ler"] == 0.017  # measured candidate_ler
    assert c["area_um2"] == 6.1
    assert c["latency_cycles"] == 8
    assert c["rtl_path"] == str(rtl)


def test_record_variant_dedupes_by_rtl_hash(tmp_path: Path):
    store_path = tmp_path / "measured_variants.jsonl"
    rtl = _make_rtl(tmp_path, "step_012_parallel.sv", "golden")

    store = MemoryStore(store_path)
    key1 = store.record_variant(_golden_record(rtl, step=12))

    # Same RTL contents -> same hash -> overwrite, not a second row.
    updated = _golden_record(rtl, step=99)
    updated.measurement.candidate_ler = 0.009
    key2 = store.record_variant(updated)

    assert key1 == key2
    assert len(store) == 1
    reloaded = MemoryStore(store_path)
    assert len(reloaded) == 1
    assert reloaded.all_records()[0].provenance.step == 99
    assert reloaded.all_records()[0].measurement.candidate_ler == 0.009


def test_record_rejects_unknown_fields(tmp_path: Path):
    """extra='forbid' guards the frozen schema — proxy fields cannot sneak in."""
    rtl = _make_rtl(tmp_path, "step_012_parallel.sv", "golden")
    with pytest.raises(Exception):
        MemoryRecord.model_validate(
            {
                "rtl_path": str(rtl),
                "design": {"bitwidth": 4, "num_layers": 2, "parallelism": 1, "pipeline_depth": 4, "window_length": 8},
                "measurement": {
                    "candidate_ler": 0.017,
                    "mwpm_ler": 0.022,
                    "suppression": 0.23,
                    "decoder_quality_multiplier": 1.5,  # forbidden proxy field
                },
                "synth": {"area_um2": 6.1, "latency_cycles": 8},
                "verification": {"layers": ["L1"], "passed": True},
                "provenance": {"step": 1, "backend": "verilator+stim+yosys"},
            }
        )


# --- MP1 integration: real synth_metrics + verify-layer shapes ----------------


def test_synth_block_adapts_real_synth_metrics_and_drops_log_path(tmp_path: Path):
    """A raw synth_metrics output adapts in; log path + cell_count are dropped.

    Synth.from_synth_metrics keeps the persisted subset (area, latency, power,
    valid) and never leaks the machine-local yosys_log_path or intermediate
    cell_count into the record.
    """
    rtl = _make_rtl(tmp_path, "step_012_parallel.sv", "golden")
    metrics = _golden_synth_metrics(rtl)  # full real SynthMetrics TypedDict

    synth = Synth.from_synth_metrics(metrics)
    assert synth.area_um2 == 6.1
    assert synth.latency_cycles == 8
    assert synth.power_mw_est == 0.048
    assert synth.valid is True

    dumped = synth.model_dump()
    assert set(dumped) == {"area_um2", "latency_cycles", "power_mw_est", "valid"}
    assert "yosys_log_path" not in dumped
    assert "cell_count" not in dumped


def test_synth_block_forbids_raw_synth_metrics_keys():
    """extra='forbid' rejects the dropped fields if a caller bypasses the adapter."""
    with pytest.raises(Exception):
        Synth(area_um2=6.1, latency_cycles=8, yosys_log_path="x.log")  # type: ignore[call-arg]


def test_real_shape_record_round_trip_and_pareto_fields(tmp_path: Path):
    """End-to-end: build a record from real-shaped MeasureResult + synth_metrics.

    Round-trips through disk, then asserts query_pareto_candidates returns
    exactly the fields C10 needs, sourced from MEASURED values only (the LER is
    the measured candidate_ler, area/latency from synth_metrics) — never a proxy.
    """
    rtl = _make_rtl(tmp_path, "step_012_parallel.sv", "golden")
    store_path = tmp_path / "measured_variants.jsonl"

    measure = _golden_measure_result(rtl)
    metrics = _golden_synth_metrics(rtl)
    record = MemoryRecord.build(
        rtl_path=str(rtl),
        design=DesignConfig(bitwidth=8, num_layers=4, parallelism=2, pipeline_depth=4, window_length=16),
        measurement=measure,          # raw MeasureResult
        synth=metrics,                # raw SynthMetrics (full real shape)
        verification=Verification.from_layers(passed=True),  # defaults to L1/L4/L5
        provenance={"step": 12, "backend": "verilator+stim+yosys"},
    )

    # Verification block reflects the REAL layer set.
    assert record.verification.layers == ["L1", "L4", "L5"]

    key = MemoryStore(store_path).record_variant(record)
    assert key == rtl_hash(rtl)

    # Reload from disk; the dropped synth_metrics keys never hit the JSONL.
    raw_line = store_path.read_text(encoding="utf-8").strip()
    assert "yosys_log_path" not in raw_line
    assert "cell_count" not in raw_line

    reloaded = MemoryStore(store_path)
    candidates = reloaded.query_pareto_candidates()
    assert len(candidates) == 1
    c = candidates[0]
    # Exactly the fields C10 needs.
    assert set(c) == {"rtl_hash", "rtl_path", "ler", "area_um2", "latency_cycles"}
    # Sourced from MEASURED values only.
    assert c["ler"] == measure["candidate_ler"] == 0.017
    assert c["area_um2"] == metrics["area_um2"] == 6.1
    assert c["latency_cycles"] == metrics["latency_cycles"] == 8
    assert c["rtl_hash"] == key
    assert c["rtl_path"] == str(rtl)
