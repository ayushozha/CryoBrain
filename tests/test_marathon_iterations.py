from __future__ import annotations

import json
from pathlib import Path

from scripts import check_marathon_iterations as checker


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_design_run(run_dir: Path) -> None:
    for name in checker.MANDATORY_RUN_FILES:
        if name.endswith(".sv"):
            (run_dir / name).write_text("module candidate; endmodule\n", encoding="utf-8")
        elif name.endswith(".md"):
            (run_dir / name).write_text("# run\n", encoding="utf-8")
        else:
            _write_json(run_dir / name, {})


def _memory_ab_payload() -> dict:
    row_a = {"step": 0, "suppression": 0.1}
    return {
        "without_memory": [row_a, {"step": 1, "suppression": 0.1}],
        "with_memory": [row_a, {"step": 1, "suppression": 0.1}],
    }


def _memory_ab_summary() -> dict:
    return {
        "with": 2,
        "without": 2,
        "with_end_reward": 0.1,
        "without_end_reward": 0.1,
        "with_slope": 0.0,
        "without_slope": 0.0,
        "endpoint_delta": 0.0,
        "slope_delta": 0.0,
        "memory_wins": False,
        "status": "memory_parity",
    }


def _write_cycle(root: Path, cycle: int) -> dict:
    cycle_dir = root / "artifacts" / "marathon_runs" / f"cycle_{cycle:03d}"
    for name in checker.REQUIRED_ARCHIVE_ENTRIES:
        if name in {"summary.json", "design_runs"}:
            continue
        payload = _memory_ab_payload() if name == "measured_memory_ab.json" else {}
        _write_json(cycle_dir / name, payload)
    for index in range(5):
        _write_design_run(cycle_dir / "design_runs" / f"d{index:03d}")

    iteration = {
        "cycle": cycle,
        "steps": 1,
        "artifact_dir": str(cycle_dir.relative_to(root)),
        "memory_ab": _memory_ab_summary(),
        "decoder": {"reward_source": "score_measured"},
        "fifo": {"reward_source": "measured_fifo_throughput"},
        "planner": {"reward_source": "score_measured"},
        "sponsors": {"fireworks": True, "modal_measure": True, "exa_research": True},
        "sponsor_evidence": {
            "required_core_sponsors": {"hud": True, "exa": True, "fireworks": True, "modal": True},
            "exa": {"live_gate": True, "hit_count": 2, "urls": ["https://example.test/paper"]},
            "fireworks": {"live_gate": True, "proposer_enabled": True},
            "modal": {"live_gate": True, "measure_enabled": True, "backend": "modal+stim+verilator+yosys"},
            "hud": {"live_gate": True},
        },
        "step_logs": {
            "decoder": [{"step": 0, "valid": True}],
            "fifo": [{"step": 0, "valid": True}],
            "planner": [{"step": 0, "valid": True}],
        },
        "decoder_attempted_this_run": 1,
        "fifo_attempted_this_run": 1,
        "planner_attempted_this_run": 1,
    }
    _write_json(cycle_dir / "summary.json", iteration)
    return iteration


def test_check_summary_accepts_archived_sponsor_iterations(tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    summary = {
        "completed_iterations": 2,
        "required_sponsors": {"hud": True, "exa": True, "fireworks": True, "modal": True},
        "iterations": [_write_cycle(tmp_path, 1), _write_cycle(tmp_path, 2)],
    }
    summary["iteration_artifact_dirs"] = [item["artifact_dir"] for item in summary["iterations"]]
    path = tmp_path / "artifacts" / "measured_50_iteration_summary.json"
    _write_json(path, summary)

    assert checker.check_summary(path, min_iterations=2) == []


def test_check_summary_blocks_missing_iteration_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    iteration = _write_cycle(tmp_path, 1)
    (tmp_path / iteration["artifact_dir"] / "measured_pareto.json").unlink()
    path = tmp_path / "artifacts" / "measured_50_iteration_summary.json"
    _write_json(
        path,
        {
            "completed_iterations": 1,
            "required_sponsors": {"hud": True, "exa": True, "fireworks": True, "modal": True},
            "iteration_artifact_dirs": [iteration["artifact_dir"]],
            "iterations": [iteration],
        },
    )

    assert any("missing archived measured_pareto.json" in error for error in checker.check_summary(path, min_iterations=1))


def test_check_summary_blocks_missing_sponsor_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    iteration = _write_cycle(tmp_path, 1)
    path = tmp_path / "artifacts" / "measured_50_iteration_summary.json"
    _write_json(
        path,
        {
            "completed_iterations": 1,
            "required_sponsors": {"hud": True, "exa": False, "fireworks": True, "modal": True},
            "iteration_artifact_dirs": [iteration["artifact_dir"]],
            "iterations": [iteration],
        },
    )

    assert any("required sponsor gate" in error for error in checker.check_summary(path, min_iterations=1))


def test_check_summary_blocks_memory_tie_marked_as_win(tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    iteration = _write_cycle(tmp_path, 1)
    iteration["memory_ab"]["memory_wins"] = True
    path = tmp_path / "artifacts" / "measured_50_iteration_summary.json"
    _write_json(
        path,
        {
            "completed_iterations": 1,
            "required_sponsors": {"hud": True, "exa": True, "fireworks": True, "modal": True},
            "iteration_artifact_dirs": [iteration["artifact_dir"]],
            "iterations": [iteration],
        },
    )

    assert any("strict positive endpoint delta" in error for error in checker.check_summary(path, min_iterations=1))
