"""C5 / MP3: measured local trainer wiring (boundary monkeypatched).

Verilator/Yosys are Linux-only, so this unit test mocks the measure+synth+score
boundary (``score_measured``) and asserts the trainer THREADS measured output
into reward + climb history + memory — without faking measured data in the
production code path. The real end-to-end climb runs in WSL
(``scripts/run_c5_climb_wsl.sh``).

What is asserted:
  (a) the loop calls the measured boundary >= 1 per step;
  (b) reward is derived from ``score_measured`` output, not a formula;
  (c) accepted steps append a climb row with ``rtl_hash`` + measured ``candidate_ler``;
  (d) a memory record is written per accepted variant via ``record_variant``;
  (e) verification failure => reward 0 / variant rejected (not recorded).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cryobrain.memory.store import MemoryStore
from cryobrain.rl import local_trainer, proposal_loop
from cryobrain.types import DesignConfig


def _valid_score(reward: float, ler: float, suppression: float) -> dict[str, Any]:
    """A measured-VALID score_measured-shaped dict (verification passed)."""
    return {
        "reward": reward,
        "valid": True,
        "ler": ler,
        "area_um2": 6.1,
        "latency_cycles": 8,
        "power_mw": 0.048,
        "layers_passed": ["L1", "L2", "L4", "L5"],
        "hard_caps": [],
        "mwpm_ler": 0.022,
        "suppression": suppression,
        "source": "measured",
        "measurement": {"candidate_ler": ler, "mwpm_ler": 0.022, "suppression": suppression},
        "synth": {"area_um2": 6.1, "latency_cycles": 8, "power_mw_est": 0.048, "valid": True},
    }


def _invalid_score() -> dict[str, Any]:
    """A measured-INVALID score (verification failed) => reward 0, rejected."""
    return {
        "reward": 0.0,
        "valid": False,
        "ler": 1.0,
        "area_um2": 0.0,
        "latency_cycles": 0,
        "power_mw": 0.0,
        "layers_passed": ["L1"],
        "hard_caps": ["l4_fail"],
        "mwpm_ler": 0.022,
        "suppression": 0.0,
        "source": "measured",
    }


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "measured_variants.jsonl")


def test_loop_calls_measured_boundary_per_step(tmp_path, monkeypatch):
    """(a) The measured boundary is hit at least once per step."""
    calls: list[Path] = []

    def fake_score(workdir: Path) -> dict[str, Any]:
        calls.append(Path(workdir))
        # A real .sv must exist (generate_rtl ran) for the hash + memory path.
        assert (Path(workdir) / "rtl" / "cryo_brain_decoder.sv").is_file()
        return _valid_score(0.3, 0.017, 0.2)

    result = local_trainer.run_measured_training(
        steps=3,
        score_fn=fake_score,
        store=_store(tmp_path),
        climb_path=tmp_path / "climb.json",
    )
    assert len(calls) == 3
    assert result["reward_source"] == "score_measured"


def test_reward_derived_from_measured_output(tmp_path, monkeypatch):
    """(b) Reward comes from score_measured["reward"], not a formula."""
    sentinel_reward = 0.4242

    def fake_score(workdir: Path) -> dict[str, Any]:
        return _valid_score(sentinel_reward, 0.015, 0.25)

    result = local_trainer.run_measured_training(
        steps=1,
        score_fn=fake_score,
        store=_store(tmp_path),
        climb_path=tmp_path / "climb.json",
    )
    assert result["steps_log"][0]["reward"] == sentinel_reward
    # And the measured LER / suppression are threaded through verbatim.
    assert result["steps_log"][0]["candidate_ler"] == 0.015
    assert result["steps_log"][0]["suppression"] == 0.25


def test_accepted_steps_append_climb_rows_with_hash_and_ler(tmp_path):
    """(c) Accepted steps append rows carrying rtl_hash + measured candidate_ler."""
    # Rising suppression => every step accepted.
    lers = iter([0.030, 0.020, 0.012])
    supps = iter([0.05, 0.15, 0.30])

    def fake_score(workdir: Path) -> dict[str, Any]:
        return _valid_score(0.3, next(lers), next(supps))

    climb = tmp_path / "climb.json"
    result = local_trainer.run_measured_training(
        steps=3,
        score_fn=fake_score,
        store=_store(tmp_path),
        climb_path=climb,
    )
    history = result["history"]
    assert len(history) == 3
    for row in history:
        assert set(row) == {"step", "candidate_ler", "suppression", "rtl_hash"}
        assert row["rtl_hash"]  # non-empty sha256 of the real generated .sv
    assert [r["candidate_ler"] for r in history] == [0.030, 0.020, 0.012]
    # Persisted climb artifact carries measured fields only.
    import json

    persisted = json.loads(climb.read_text(encoding="utf-8"))
    assert persisted["reward_source"] == "score_measured"
    assert len(persisted["history"]) == 3


def test_memory_record_written_per_accepted_variant(tmp_path):
    """(d) One memory record per accepted, valid variant (distinct RTL hashes)."""
    supps = iter([0.05, 0.15, 0.30])

    def fake_score(workdir: Path) -> dict[str, Any]:
        return _valid_score(0.3, 0.02, next(supps))

    store = _store(tmp_path)
    local_trainer.run_measured_training(
        steps=3,
        score_fn=fake_score,
        store=store,
        climb_path=tmp_path / "climb.json",
    )
    # 3 distinct preset designs => 3 distinct RTL => 3 records, all verified.
    assert len(store) == 3
    for rec in store.all_records():
        assert rec.verification.passed is True
        # Measured candidate_ler, never a proxy field.
        assert rec.measurement.candidate_ler == 0.02


def test_verification_failure_zeroes_reward_and_rejects(tmp_path):
    """(e) Verification failure => reward 0, not recorded, not in climb."""
    def fake_score(workdir: Path) -> dict[str, Any]:
        return _invalid_score()

    store = _store(tmp_path)
    result = local_trainer.run_measured_training(
        steps=2,
        score_fn=fake_score,
        store=store,
        climb_path=tmp_path / "climb.json",
    )
    assert all(s["reward"] == 0.0 for s in result["steps_log"])
    assert all(s["valid"] is False for s in result["steps_log"])
    assert all(s["recorded"] is False for s in result["steps_log"])
    assert result["history"] == []  # nothing climbs on a failed gate
    assert len(store) == 0  # rejected variants never enter memory


def test_measured_reward_boundary_for_c4(tmp_path):
    """The reward_fn boundary C4/GRPO consumes: design -> (reward, score, rtl_path)."""
    def fake_score(workdir: Path) -> dict[str, Any]:
        return _valid_score(0.55, 0.011, 0.33)

    scenario = local_trainer._load_scenario()
    reward, score, rtl_path = proposal_loop.measured_reward(
        DesignConfig(),
        scenario,
        score_fn=fake_score,
    )
    assert reward == 0.55
    assert score["suppression"] == 0.33
    assert Path(rtl_path).is_file()  # real generated RTL


def test_step_result_climb_row_shape(tmp_path):
    """A single step's StepResult exposes the measured climb row contract."""
    def fake_score(workdir: Path) -> dict[str, Any]:
        return _valid_score(0.3, 0.018, 0.21)

    result = proposal_loop.run_proposal_step(
        step=7,
        design=DesignConfig(),
        scenario=local_trainer._load_scenario(),
        store=_store(tmp_path),
        score_fn=fake_score,
    )
    row = result.climb_row()
    assert row["step"] == 7
    assert row["candidate_ler"] == 0.018
    assert row["suppression"] == 0.21
    assert row["rtl_hash"]
    assert result.recorded is True
