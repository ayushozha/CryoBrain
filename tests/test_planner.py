"""SPEC-v6 P-train2: Planner agent unit tests (boundary monkeypatched).

Verilator/Yosys are Linux-only; these tests mock ``score_measured`` and assert:
  (a) plan selection is deterministic given seed + step + history;
  (b) planner climb artifact matches measured_climb row schema + planner_source;
  (c) planner_reward tracks measured suppression delta.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cryobrain.artifacts.schemas.v2 import validate_measured_climb
from cryobrain.memory.store import MemoryStore
from cryobrain.rl import planner_trainer
from cryobrain.swarm.event_bus import EventBus
from cryobrain.swarm.planner import KNOBS, Planner


def _valid_score(reward: float, ler: float, suppression: float) -> dict[str, Any]:
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


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "measured_variants.jsonl")


def test_plan_selection_deterministic_with_seed():
    """Same seed + step + history => identical knob and direction."""
    bus = EventBus(log_path=None)
    p1 = Planner(seed=42, bus=bus, explore_rate=0.0)
    p2 = Planner(seed=42, bus=EventBus(log_path=None), explore_rate=0.0)

    history = [{"step": 0, "candidate_ler": 0.02, "suppression": 0.1, "rtl_hash": "abc"}]
    plans_log = [
        {"step": 0, "knob": "bitwidth", "planner_reward": 0.05, "direction": "explore"},
        {"step": 1, "knob": "parallelism", "planner_reward": 0.12, "direction": "exploit"},
    ]

    for step in (2, 3, 4):
        a = p1.plan(step, climb_history=history, plans_log=plans_log)
        b = p2.plan(step, climb_history=history, plans_log=plans_log)
        assert a["knob"] == b["knob"]
        assert a["direction"] == b["direction"]
        assert a["knob"] in KNOBS

    # Cold start is round-robin by step.
    cold = Planner(seed=7, bus=EventBus(log_path=None), explore_rate=0.0)
    assert cold.plan(0)["knob"] == KNOBS[0]
    assert cold.plan(1)["knob"] == KNOBS[1]


def test_apply_plan_mutates_chosen_knob_only():
    """Architect hook changes only the knob named in the plan."""
    planner = Planner(seed=0, bus=EventBus(log_path=None))
    plan = planner.plan(0)
    before = plan["base_design"]
    design = planner.apply_plan(plan)
    after = design.to_dict()

    changed = [k for k in before if before[k] != after[k]]
    assert changed == [plan["knob"]]


def test_planner_emits_bus_events():
    bus = EventBus(log_path=None)
    planner = Planner(seed=1, bus=bus)
    planner.plan(0)
    assert bus.events()[0]["agent"] == "Planner"  # Agent.PLANNER
    assert bus.events()[0]["action"] == "plan"


def test_planner_climb_artifact_schema(tmp_path):
    """Planner climb artifact validates as measured_climb + planner_source tag."""
    supps = iter([0.05, 0.15, 0.30])

    def fake_score(workdir: Path) -> dict[str, Any]:
        return _valid_score(0.3, 0.02, next(supps))

    climb = tmp_path / "planner_climb.json"
    result = planner_trainer.run_planner_training(
        steps=3,
        seed=0,
        score_fn=fake_score,
        store=_store(tmp_path),
        climb_path=climb,
        bus=EventBus(log_path=None),
    )

    assert result["reward_source"] == "score_measured"
    assert result["planner_source"] == "cryobrain.swarm.planner"
    assert len(result["history"]) == 3

    persisted = json.loads(climb.read_text(encoding="utf-8"))
    assert persisted["planner_source"] == "cryobrain.swarm.planner"
    assert set(persisted) >= {"backend", "reward_source", "planner_source", "steps", "history"}
    for row in persisted["history"]:
        assert {"step", "candidate_ler", "suppression", "rtl_hash"} <= set(row)

    # Row schema is identical to measured_climb (extra top-level tag is fine).
    validate_measured_climb(persisted)


def test_planner_reward_tracks_suppression_delta(tmp_path):
    """Planner earns measured delta when suppression improves."""
    supps = iter([0.05, 0.20, 0.35])

    def fake_score(workdir: Path) -> dict[str, Any]:
        return _valid_score(0.3, 0.02, next(supps))

    result = planner_trainer.run_planner_training(
        steps=3,
        seed=0,
        score_fn=fake_score,
        store=_store(tmp_path),
        climb_path=None,
        bus=EventBus(log_path=None),
    )

    rewards = [row["planner_reward"] for row in result["plans_log"]]
    assert rewards[0] == pytest.approx(0.05)  # first valid step sets baseline
    assert rewards[1] == pytest.approx(0.15)  # 0.20 - 0.05
    assert rewards[2] == pytest.approx(0.15)  # 0.35 - 0.20
