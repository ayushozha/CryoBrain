"""Swarm event-log visualization rules (SPEC-v6 P-viz)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cryobrain.swarm.visualization import (
    STATUS_IN_PROGRESS,
    STATUS_RESULT,
    build_swarm_timeline,
    load_event_log,
    normalize_event,
)


def _write_log(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_normalize_event_measured_true_is_result():
    raw = {
        "ts": "2026-06-20T12:00:00Z",
        "agent": "Measurement",
        "action": "measure",
        "design_id": "d017",
        "payload": {"candidate_ler": 0.041},
        "measured": True,
        "artifact_ref": "artifacts/measured/d017.json",
    }
    event = normalize_event(raw)
    assert event["status"] == STATUS_RESULT
    assert event["measured"] is True
    assert event["artifact_ref"] == "artifacts/measured/d017.json"


def test_normalize_event_without_measured_is_in_progress():
    raw = {
        "ts": "2026-06-20T12:00:01Z",
        "agent": "Architect",
        "action": "propose",
        "design_id": "d017",
        "payload": {"bitwidth": 4},
    }
    event = normalize_event(raw)
    assert event["status"] == STATUS_IN_PROGRESS
    assert event["measured"] is False


def test_measured_false_string_is_in_progress():
    """Only strict ``measured: true`` counts as a finalized result."""
    event = normalize_event(
        {
            "agent": "Measurement",
            "action": "measure",
            "design_id": "d1",
            "measured": "true",
            "artifact_ref": "artifacts/measured/d1.json",
        }
    )
    assert event["status"] == STATUS_IN_PROGRESS


def test_load_event_log_skips_blank_lines(tmp_path: Path):
    log = tmp_path / "event_log.jsonl"
    _write_log(
        log,
        [
            {"agent": "Research", "action": "fetch", "design_id": "d1"},
            {"agent": "Architect", "action": "propose", "design_id": "d1"},
        ],
    )
    log.write_text(log.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    events = load_event_log(log)
    assert len(events) == 2
    assert all(e["status"] == STATUS_IN_PROGRESS for e in events)


def test_build_swarm_timeline_counts_results_vs_in_progress(tmp_path: Path):
    log = tmp_path / "swarm" / "event_log.jsonl"
    _write_log(
        log,
        [
            {"agent": "Research", "action": "fetch", "design_id": "d1"},
            {
                "agent": "Measurement",
                "action": "measure",
                "design_id": "d1",
                "measured": True,
                "artifact_ref": "artifacts/measured/d1.json",
            },
            {"agent": "Architect", "action": "propose", "design_id": "d2"},
        ],
    )
    timeline = build_swarm_timeline(log)
    assert timeline is not None
    assert timeline["summary"] == {"total": 3, "results": 1, "in_progress": 2}
    assert timeline["events"][1]["status"] == STATUS_RESULT
    assert timeline["events"][0]["status"] == STATUS_IN_PROGRESS


def test_build_swarm_timeline_missing_log_returns_none(tmp_path: Path):
    assert build_swarm_timeline(tmp_path / "missing.jsonl") is None


def test_invalid_jsonl_raises(tmp_path: Path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSONL"):
        load_event_log(bad)