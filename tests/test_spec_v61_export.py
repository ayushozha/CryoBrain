from __future__ import annotations

import json
from pathlib import Path

from scripts import export_spec_v61_artifacts as exporter


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run_events(design_id: str, rtl: Path, ler: float, score_ref: str, measure_ref: str) -> list[dict]:
    return [
        {"agent": "Research", "action": "context_pack", "design_id": design_id, "payload": {"urls": []}},
        {
            "agent": "Architect",
            "action": "propose",
            "design_id": design_id,
            "payload": {"bitwidth": 4, "num_layers": 2, "parallelism": 1, "pipeline_depth": 4, "window_length": 8},
        },
        {"agent": "RTL", "action": "generate", "design_id": design_id, "payload": {"rtl_path": str(rtl)}},
        {
            "agent": "Measurement",
            "action": "measure",
            "design_id": design_id,
            "payload": {"candidate_ler": ler, "suppression": 1.0 - ler},
            "measured": True,
            "artifact_ref": measure_ref,
        },
        {"agent": "Verifier", "action": "verify", "design_id": design_id, "payload": {"valid": True}},
        {
            "agent": "Scorer",
            "action": "score",
            "design_id": design_id,
            "payload": {"valid": True, "ler": ler, "suppression": 1.0 - ler},
            "measured": True,
            "artifact_ref": score_ref,
        },
        {"agent": "Memory", "action": "record_variant", "design_id": design_id, "payload": {"rtl_hash": f"h{ler}"}},
    ]


def test_export_design_runs_keeps_reused_design_ids_coherent(tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    monkeypatch.setattr(exporter, "DESIGN_RUNS", tmp_path / "artifacts" / "design_runs")

    rtl = tmp_path / "candidate.sv"
    rtl.write_text("module candidate; endmodule\n", encoding="utf-8")

    log = tmp_path / "artifacts" / "swarm" / "event_log.jsonl"
    first_measure = "artifacts/measured/d000-first.json"
    first_score = "artifacts/scores/d000-first.json"
    second_measure = "artifacts/measured/d000-second.json"
    second_score = "artifacts/scores/d000-second.json"
    _write_json(tmp_path / first_measure, {"design_id": "d000", "measurement": {"candidate_ler": 0.1, "suppression": 0.9}})
    _write_json(tmp_path / first_score, {"design_id": "d000", "valid": True, "ler": 0.1, "suppression": 0.9})
    _write_json(tmp_path / second_measure, {"design_id": "d000", "measurement": {"candidate_ler": 0.2, "suppression": 0.8}})
    _write_json(tmp_path / second_score, {"design_id": "d000", "valid": True, "ler": 0.2, "suppression": 0.8})

    events = [
        *_run_events("d000", rtl, 0.1, first_score, first_measure),
        *_run_events("d000", rtl, 0.2, second_score, second_measure),
    ]
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    assert exporter.export_design_runs(log_path=log, limit=2) == ["d000", "d001"]
    first = json.loads((tmp_path / "artifacts" / "design_runs" / "d000" / "score.json").read_text(encoding="utf-8"))
    second = json.loads((tmp_path / "artifacts" / "design_runs" / "d001" / "score.json").read_text(encoding="utf-8"))
    assert first["ler"] == 0.1
    assert second["ler"] == 0.2
