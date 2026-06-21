"""Demo bundle prefers measured artifacts when fixtures exist (SPEC-v6 truth-up)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_demo import MissingMeasuredArtifactsError, build_bundle  # noqa: E402


def _measured_climb_fixture() -> dict:
    return {
        "backend": "verilator+stim+yosys",
        "reward_source": "score_measured",
        "history": [
            {"step": 0, "candidate_ler": 0.05, "suppression": 0.10, "rtl_hash": "aaa"},
            {"step": 1, "candidate_ler": 0.04, "suppression": 0.20, "rtl_hash": "bbb"},
        ],
    }


def _measured_memory_fixture() -> dict:
    row_a = {"step": 0, "candidate_ler": 0.05, "suppression": 0.10, "rtl_hash": "aaa"}
    row_b = {"step": 1, "candidate_ler": 0.04, "suppression": 0.15, "rtl_hash": "bbb"}
    return {
        "reward_source": "score_measured",
        "without_memory": [row_a, {"step": 1, "candidate_ler": 0.045, "suppression": 0.12, "rtl_hash": "ccc"}],
        "with_memory": [row_a, row_b],
    }


def _measured_memory_tie_fixture() -> dict:
    row_a = {"step": 0, "candidate_ler": 0.05, "suppression": 0.10, "rtl_hash": "aaa"}
    row_b = {"step": 1, "candidate_ler": 0.04, "suppression": 0.15, "rtl_hash": "bbb"}
    return {
        "reward_source": "score_measured",
        "without_memory": [row_a, row_b],
        "with_memory": [row_a, row_b],
    }


def _measured_fifo_fixture() -> dict:
    return {
        "backend": "verilator+fifo-throughput",
        "reward_source": "measured_fifo_throughput",
        "target": "stream_arb_fifo",
        "history": [
            {"step": 0, "throughput": 0.1, "suppression": 0.05, "rtl_hash": "fifo_a"},
            {"step": 1, "throughput": 0.35, "suppression": 0.30, "rtl_hash": "fifo_b"},
            {"step": 2, "throughput": 0.42, "suppression": 0.38, "rtl_hash": "fifo_c"},
        ],
    }


def _measured_pareto_fixture() -> dict:
    return {
        "points": [
            {
                "label": "variant_a@abc",
                "ler": 0.018,
                "area_um2": 5000.0,
                "latency_cycles": 8,
                "rtl_path": "artifacts/variants/a.sv",
                "on_frontier": True,
            },
            {
                "label": "variant_b@def",
                "ler": 0.025,
                "area_um2": 3000.0,
                "latency_cycles": 6,
                "rtl_path": "artifacts/variants/b.sv",
                "on_frontier": True,
            },
        ]
    }


def _proxy_climb_fixture() -> dict:
    return {
        "history": [{"step": 0, "reward": 0.3}, {"step": 1, "reward": 0.5}],
        "summary": {"start_reward": 0.3, "end_reward": 0.5},
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_demo_prefers_measured_artifacts(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    _write_json(artifacts / "measured_climb.json", _measured_climb_fixture())
    _write_json(artifacts / "measured_fifo_climb.json", _measured_fifo_fixture())
    _write_json(artifacts / "measured_memory_ab.json", _measured_memory_fixture())
    _write_json(artifacts / "measured_pareto.json", _measured_pareto_fixture())
    # Proxy-era files present but must lose to measured.
    _write_json(artifacts / "climb_chart_rl.json", _proxy_climb_fixture())
    _write_json(artifacts / "designs.json", [{"name": "proxy_only", "kind": "policy", "reward": 0.99}])

    bundle = build_bundle(artifacts)

    assert bundle["data_era"] == "measured"
    assert bundle["sources"]["climb"] == "artifacts/measured_climb.json"
    assert bundle["sources"]["fifo_climb"] == "artifacts/measured_fifo_climb.json"
    assert bundle["sources"]["memory"] == "artifacts/measured_memory_ab.json"
    assert bundle["sources"]["pareto"] == "artifacts/measured_pareto.json"
    assert bundle["sources"]["climb_era"] == "measured"
    assert bundle["sources"]["fifo_era"] == "measured"
    assert bundle["climb"]["reward_source"] == "score_measured"
    assert bundle["climb"]["history"][1]["reward"] == 0.20
    assert bundle["fifo_climb"]["history"][2]["throughput"] == 0.42
    assert bundle["improvement"]["agents_keep_improving"] is True
    assert any(t["target"] == "stream_arb_fifo" for t in bundle["improvement"]["tracks"])
    assert bundle["memory"]["with_memory"]["end_reward"] == 0.15
    assert bundle["memory"]["memory_wins"] is True
    assert bundle["memory"]["endpoint_delta"] == 0.03
    assert len(bundle["pareto"]["points"]) == 2
    assert bundle["pareto"]["points"][0]["ler"] == 0.018


def test_build_demo_does_not_count_memory_tie_as_win(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    _write_json(artifacts / "measured_climb.json", _measured_climb_fixture())
    _write_json(artifacts / "measured_fifo_climb.json", _measured_fifo_fixture())
    _write_json(artifacts / "measured_memory_ab.json", _measured_memory_tie_fixture())
    _write_json(artifacts / "measured_pareto.json", _measured_pareto_fixture())

    bundle = build_bundle(artifacts)

    assert bundle["memory"]["memory_wins"] is False
    assert bundle["memory"]["endpoint_delta"] == 0.0
    assert bundle["memory"]["slope_delta"] == 0.0
    assert bundle["memory"]["status"] == "memory_parity"


def test_build_demo_rejects_proxy_only_artifacts(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    _write_json(artifacts / "climb_chart_rl.json", _proxy_climb_fixture())
    _write_json(
        artifacts / "designs_rl.json",
        [
            {
                "name": "policy_a",
                "kind": "policy",
                "reward": 0.6,
                "ler_suppression": 0.2,
                "area_mm2": 0.000006,
                "latency_cycles": 10,
            }
        ],
    )

    with pytest.raises(MissingMeasuredArtifactsError):
        build_bundle(artifacts)


def test_build_demo_includes_swarm_timeline_when_log_present(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    _write_json(artifacts / "measured_climb.json", _measured_climb_fixture())
    _write_json(artifacts / "measured_fifo_climb.json", _measured_fifo_fixture())
    _write_json(artifacts / "measured_memory_ab.json", _measured_memory_fixture())
    _write_json(artifacts / "measured_pareto.json", _measured_pareto_fixture())
    log = artifacts / "swarm" / "event_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    measured_artifact = artifacts / "measured" / "d1.json"
    measured_artifact.parent.mkdir(parents=True, exist_ok=True)
    measured_artifact.write_text(
        json.dumps({"design_id": "d1", "measurement": {"candidate_ler": 0.017}}),
        encoding="utf-8",
    )
    log.write_text(
        "\n".join(
            [
                json.dumps({"agent": "Architect", "action": "propose", "design_id": "d1"}),
                json.dumps(
                    {
                        "agent": "Measurement",
                        "action": "measure",
                        "design_id": "d1",
                        "payload": {"candidate_ler": 0.017},
                        "measured": True,
                        "artifact_ref": str(measured_artifact),
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = build_bundle(artifacts)

    assert bundle["swarm_timeline"] is not None
    assert bundle["swarm_timeline"]["summary"]["results"] == 1
    assert bundle["swarm_timeline"]["events"][1]["status"] == "result"
