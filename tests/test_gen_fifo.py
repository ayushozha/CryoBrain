"""C9 / GEN: FIFO second-target measured optimization (SPEC-v5 §6).

Two layers, like ``test_local_trainer_measured.py``:

(a) UNIT (Windows-default): the FIFO generator emits distinct ``.sv`` for distinct
    configs; the stim traffic is valid; the optimization STEP wiring (sim/measure
    boundary MOCKED) records a FIFO variant to the SHARED memory store with a
    MEASURED metric, and a verification-gate failure rejects the variant. No fake
    measured numbers in the production path — the mock stands in for the real sim.

(b) ``@pytest.mark.wsl`` INTEGRATION: over N steps the optimizer IMPROVES the
    MEASURED FIFO throughput (the GEN gate) — real cocotb+Verilator sim, WSL-only.
    Skipped on Windows (no Verilator).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cryobrain.memory.store import MemoryStore
from cryobrain.rl import fifo_loop
from cryobrain.rtl_gen.fifo_generator import generate_fifo_rtl, render_fifo_rtl
from cryobrain.stim import fifo_stim
from cryobrain.types_fifo import FifoConfig, fifo_preset_variants


# --- (a) UNIT: generator ------------------------------------------------------


def test_distinct_configs_produce_distinct_rtl(tmp_path):
    """Distinct FifoConfigs -> distinct generated .sv (the GEN P1-style proof)."""
    a = render_fifo_rtl(FifoConfig(depth=2, width=8))
    b = render_fifo_rtl(FifoConfig(depth=16, width=8))
    c = render_fifo_rtl(FifoConfig(depth=16, width=32))
    assert a != b != c and a != c
    # depth/width land in the real parameter defaults of the generated module.
    assert "depth_p = 2" in a and "depth_p = 16" in b
    assert "width_p = 32" in c


def test_generate_fifo_rtl_writes_file(tmp_path):
    """generate_fifo_rtl writes a synthesizable-looking .sv at the expected path."""
    path = generate_fifo_rtl(FifoConfig(depth=8, width=16), tmp_path / "rtl")
    assert path.name == "stream_arb_fifo.sv"
    text = path.read_text(encoding="utf-8")
    assert "module stream_arb_fifo" in text and "endmodule" in text


def test_invalid_config_rejected():
    """A non-synthesizable config (depth < 2) is rejected before emitting RTL."""
    with pytest.raises(ValueError):
        render_fifo_rtl(FifoConfig(depth=1, width=8))


# --- (a) UNIT: stim -----------------------------------------------------------


def test_stim_produces_valid_vectors():
    """fifo_stim yields well-formed per-cycle traffic vectors."""
    traffic = fifo_stim.generate_traffic(cycles=32, width=8, seed=1729)
    assert len(traffic) == 32
    rows = fifo_stim.to_vector_rows(traffic)
    for row in rows:
        assert set(row) == {"valid0", "data0", "valid1", "data1", "yumi"}
        assert row["valid0"] in (0, 1) and row["valid1"] in (0, 1) and row["yumi"] in (0, 1)
        assert 0 <= row["data0"] <= 0xFF and 0 <= row["data1"] <= 0xFF


def test_reference_throughput_monotone_in_depth():
    """The measured-metric DIRECTION is checkable: deeper FIFO drains >= shallower.

    This is the property the GEN gate relies on — it makes the optimizer's climb a
    real signal, not noise. Computed from the cycle-accurate golden reference.
    """
    traffic = fifo_stim.generate_traffic(cycles=64, width=8, seed=1729)
    drained = [fifo_stim.reference_drained(traffic, depth=d) for d in (1, 2, 4, 8, 16)]
    assert drained == sorted(drained)  # non-decreasing
    assert drained[-1] > drained[0]  # and strictly improves end-to-end


# --- (a) UNIT: optimization step wiring (sim boundary mocked) ------------------


def _valid_fifo_score(throughput: float, baseline: float = 0.05) -> dict[str, Any]:
    """A measured-VALID FIFO score (correctness gate passed)."""
    return {
        "reward": throughput,
        "valid": True,
        "throughput": throughput,
        "baseline_throughput": baseline,
        "suppression": throughput - baseline,
        "drained": int(throughput * 64),
        "cycles": 64,
        "layers_passed": ["L1"],
        "source": "measured-fifo-sim",
    }


def _invalid_fifo_score() -> dict[str, Any]:
    """A measured-INVALID FIFO score (DUT diverged from golden) => reward 0."""
    return {
        "reward": 0.0,
        "valid": False,
        "throughput": 0.0,
        "baseline_throughput": 0.05,
        "suppression": 0.0,
        "drained": 0,
        "cycles": 64,
        "layers_passed": [],
        "source": "measured-fifo-sim",
    }


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "measured_variants.jsonl")


def test_step_records_fifo_variant_to_shared_memory(tmp_path):
    """A measured-valid step records a FIFO variant in the SAME MemoryStore."""
    captured: list[Path] = []

    def fake_score(rtl_path: Path, design: FifoConfig) -> dict[str, Any]:
        captured.append(Path(rtl_path))
        assert Path(rtl_path).is_file()  # generate_fifo_rtl ran (real .sv on disk)
        return _valid_fifo_score(0.3)

    store = _store(tmp_path)
    result = fifo_loop.run_fifo_step(
        step=4,
        design=FifoConfig(depth=8, width=8),
        store=store,
        score_fn=fake_score,
        out_dir=tmp_path / "step4",
    )
    assert len(captured) == 1
    assert result.recorded is True and result.valid is True
    assert result.throughput == 0.3
    # The variant is in the shared store, carrying MEASURED fields + FIFO backend.
    assert len(store) == 1
    rec = store.all_records()[0]
    assert rec.provenance.backend == fifo_loop.BACKEND
    assert rec.design == {"depth": 8, "width": 8}
    # throughput maps to (1 - candidate_ler); suppression is the measured gain.
    assert rec.measurement.candidate_ler == pytest.approx(0.7)
    assert rec.measurement.suppression == pytest.approx(0.25)
    assert rec.verification.passed is True


def test_step_reward_is_measured_not_formula(tmp_path):
    """Reward comes from the measured score's throughput, threaded verbatim."""
    def fake_score(rtl_path: Path, design: FifoConfig) -> dict[str, Any]:
        return _valid_fifo_score(0.4242)

    result = fifo_loop.run_fifo_step(
        step=0,
        design=FifoConfig(depth=4),
        store=_store(tmp_path),
        score_fn=fake_score,
        out_dir=tmp_path / "s0",
    )
    assert result.reward == 0.4242 and result.throughput == 0.4242


def test_correctness_failure_zeroes_reward_and_rejects(tmp_path):
    """Correctness-gate failure => reward 0, variant not recorded (mirrors decoder)."""
    def fake_score(rtl_path: Path, design: FifoConfig) -> dict[str, Any]:
        return _invalid_fifo_score()

    store = _store(tmp_path)
    result = fifo_loop.run_fifo_step(
        step=0,
        design=FifoConfig(depth=8),
        store=store,
        score_fn=fake_score,
        out_dir=tmp_path / "bad",
    )
    assert result.reward == 0.0 and result.valid is False and result.recorded is False
    assert len(store) == 0


def test_training_climb_threads_measured_throughput(tmp_path):
    """Over steps, rising MEASURED throughput climbs + records to shared memory.

    The sim boundary is mocked with a depth->throughput map (mirroring the real
    reference monotonicity); the trainer must accept improving steps, append climb
    rows with rtl_hash + measured throughput, and record one variant per accepted.
    """
    # Measured throughput keyed by the proposed design's depth (mock of real sim).
    depth_tp = {2: 0.10, 8: 0.30, 16: 0.45, 32: 0.50}

    def fake_score(rtl_path: Path, design: FifoConfig) -> dict[str, Any]:
        return _valid_fifo_score(depth_tp.get(design.depth, 0.10))

    store = _store(tmp_path)
    climb = tmp_path / "fifo_climb.json"
    result = fifo_loop.run_fifo_training(
        steps=4,
        score_fn=fake_score,
        store=store,
        climb_path=climb,
    )
    assert result["reward_source"] == "measured_fifo_throughput"
    assert result["target"] == "stream_arb_fifo"
    history = result["history"]
    # Presets are depth 2,8,16 (rising) then a deepened mutation -> climb improves.
    assert len(history) >= 3
    throughputs = [row["throughput"] for row in history]
    assert throughputs == sorted(throughputs)
    assert throughputs[-1] > throughputs[0]  # measured climb
    for row in history:
        assert set(row) == {"step", "throughput", "suppression", "rtl_hash"}
        assert row["rtl_hash"]  # real sha256 of the generated .sv
    # Persisted climb artifact carries measured fields only.
    persisted = json.loads(climb.read_text(encoding="utf-8"))
    assert persisted["reward_source"] == "measured_fifo_throughput"
    # Distinct designs -> distinct RTL hashes -> distinct memory records.
    assert len(store) == len({r.rtl_path for r in store.all_records()})
    assert len(store) >= 3


# --- (b) WSL INTEGRATION: the real GEN gate -----------------------------------


@pytest.mark.wsl
def test_gen_gate_optimizer_improves_measured_fifo_throughput(tmp_path):
    """GEN gate: over steps the optimizer IMPROVES MEASURED FIFO throughput.

    Real cocotb+Verilator sim (no mock). WSL-only — skipped on Windows where the
    EDA toolchain is absent. Asserts: (1) accepted variants exist, (2) measured
    throughput strictly improves end-to-end, (3) variants land in shared memory.
    """
    from cryobrain.rtl_grader.flow import eda_tools_available

    if not eda_tools_available():
        pytest.skip("Verilator/Yosys not available (Windows / no OSS CAD Suite)")

    store = MemoryStore(tmp_path / "measured_variants.jsonl")
    result = fifo_loop.run_fifo_training(
        steps=5,
        store=store,
        climb_path=tmp_path / "fifo_climb.json",
    )
    history = result["history"]
    assert len(history) >= 2, "GEN: optimizer produced no measured climb"
    throughputs = [row["throughput"] for row in history]
    assert throughputs[-1] > throughputs[0], "GEN gate: measured throughput must improve"
    assert len(store) >= 2  # measured FIFO variants recorded in the shared store
    for rec in store.all_records():
        assert rec.provenance.backend == fifo_loop.BACKEND
        assert rec.verification.passed is True
