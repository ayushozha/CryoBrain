"""SPEC-v6 P-bus: swarm event log schema and append/read contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cryobrain.swarm.event_bus import (
    ALL_AGENTS,
    Agent,
    EventBus,
    EventBusError,
    SwarmEvent,
    validate_event_dict,
)


def test_agent_constants_cover_nine_roles():
    assert len(ALL_AGENTS) == 9
    assert Agent.RESEARCH == "Research"
    assert Agent.VISUALIZATION == "Visualization"
    assert "Planner" in ALL_AGENTS


def test_swarm_event_schema_round_trip():
    event = SwarmEvent(
        ts="2026-06-20T12:00:00+00:00",
        agent=Agent.ARCHITECT,
        action="propose",
        design_id="d017",
        payload={"bitwidth": 4, "num_layers": 2},
    )
    raw = event.to_dict()
    assert raw == {
        "ts": "2026-06-20T12:00:00+00:00",
        "agent": "Architect",
        "action": "propose",
        "design_id": "d017",
        "payload": {"bitwidth": 4, "num_layers": 2},
    }
    assert SwarmEvent.from_dict(raw).to_dict() == raw


def test_validate_event_dict_requires_measured_artifact_ref():
    base = {
        "ts": "t",
        "agent": Agent.MEASUREMENT,
        "action": "measure",
        "design_id": "d001",
        "payload": {"candidate_ler": 0.04},
        "measured": True,
    }
    with pytest.raises(EventBusError, match="artifact_ref"):
        validate_event_dict(base)

    ok = {**base, "artifact_ref": "artifacts/measured/d001.json"}
    assert validate_event_dict(ok)["artifact_ref"] == "artifacts/measured/d001.json"


def test_event_bus_append_and_read_tail(tmp_path: Path):
    log_path = tmp_path / "event_log.jsonl"
    bus = EventBus(log_path)

    bus.emit(
        agent=Agent.RESEARCH,
        action="context_pack",
        design_id="d001",
        payload={"hit_count": 0},
    )
    bus.emit(
        agent=Agent.MEASUREMENT,
        action="measure",
        design_id="d001",
        payload={"candidate_ler": 0.041},
        measured=True,
        artifact_ref="artifacts/measured/d001.json",
    )
    bus.emit(
        agent=Agent.VERIFIER,
        action="verify",
        design_id="d001",
        payload={"layers_passed": ["L1"]},
    )

    tail = bus.read_tail(2)
    assert len(tail) == 2
    assert tail[0]["agent"] == "Measurement"
    assert tail[1]["agent"] == "Verifier"

    all_events = bus.read_all()
    assert len(all_events) == 3
    assert json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])["agent"] == "Research"


def test_read_measured_filters_measured_true_only(tmp_path: Path):
    bus = EventBus(tmp_path / "event_log.jsonl")
    bus.emit(
        agent=Agent.ARCHITECT,
        action="propose",
        design_id="d002",
        payload={"bitwidth": 4},
    )
    bus.emit(
        agent=Agent.MEASUREMENT,
        action="measure",
        design_id="d002",
        payload={"candidate_ler": 0.05},
        measured=True,
        artifact_ref="artifacts/measured/d002.json",
    )
    bus.emit(
        agent=Agent.SCORER,
        action="score",
        design_id="d002",
        payload={"reward": 0.2, "valid": False},
    )

    measured = bus.read_measured()
    assert len(measured) == 1
    assert measured[0]["agent"] == "Measurement"
    assert measured[0]["measured"] is True


def test_emit_rejects_measured_without_artifact_ref(tmp_path: Path):
    bus = EventBus(tmp_path / "event_log.jsonl")
    with pytest.raises(EventBusError, match="artifact_ref"):
        bus.emit(
            agent=Agent.SCORER,
            action="score",
            design_id="d003",
            payload={"reward": 0.1},
            measured=True,
        )