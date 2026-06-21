#!/usr/bin/env python3
"""Validate SPEC-v6.1 submission checkpoints C0–C10 (§10)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PIPELINE = (
    "Research",
    "Planner",
    "Architect",
    "RTL",
    "Measurement",
    "Verifier",
    "Scorer",
    "Memory",
)

MANDATORY_RUN_FILES = (
    "research_context.json",
    "plan.json",
    "design_config.json",
    "generated_decoder.sv",
    "verilator_result.json",
    "yosys_metrics.json",
    "stim_ler_result.json",
    "verification_report.json",
    "score.json",
    "memory_update.json",
    "run_summary.md",
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _consistent_measurement_score(run_dir: Path) -> bool:
    measurement = _load_json(run_dir / "stim_ler_result.json")
    score = _load_json(run_dir / "score.json")
    score_measurement = score.get("measurement") if isinstance(score.get("measurement"), dict) else {}
    if "candidate_ler" in measurement and score.get("ler") is not None:
        if float(measurement["candidate_ler"]) != float(score["ler"]):
            return False
    if "suppression" in measurement and score.get("suppression") is not None:
        if float(measurement["suppression"]) != float(score["suppression"]):
            return False
    for key in ("candidate_ler", "suppression"):
        if key in measurement and key in score_measurement:
            if float(measurement[key]) != float(score_measurement[key]):
                return False
    return True


def check_c0() -> tuple[bool, str]:
    climb = ROOT / "artifacts" / "measured_climb.json"
    if not climb.is_file():
        return False, "missing measured_climb.json"
    data = _load_json(climb)
    if data.get("reward_source") != "score_measured":
        return False, "climb must use score_measured"
    return True, "MP0–MP2 spine: score_measured reward path"


def check_c1() -> tuple[bool, str]:
    climb = _load_json(ROOT / "artifacts" / "measured_climb.json")
    history = climb.get("history", [])
    if not history:
        return False, "climb history empty"
    note = f"{len(history)} accepted step(s); early climb is honest"
    return True, note


def check_c2() -> tuple[bool, str]:
    run_dirs = sorted((ROOT / "artifacts" / "design_runs").glob("d*"))
    run_dirs = [path for path in run_dirs if path.is_dir()]
    if len(run_dirs) < 5:
        return False, f"need 5+ design cycles, have {len(run_dirs)}"
    incomplete: list[str] = []
    for run_dir in run_dirs[:5]:
        missing = [name for name in MANDATORY_RUN_FILES if not (run_dir / name).is_file()]
        if missing:
            incomplete.append(f"{run_dir.name}: missing {missing}")
            continue
        if not _consistent_measurement_score(run_dir):
            incomplete.append(f"{run_dir.name}: score/measurement mismatch")
    if incomplete:
        return False, "; ".join(incomplete)
    return True, f"{len(run_dirs)} design_runs with mandatory artifacts"


def check_c3() -> tuple[bool, str]:
    pareto = _load_json(ROOT / "artifacts" / "measured_pareto.json")
    count = int(pareto.get("count", 0))
    if count < 2:
        return False, f"pareto needs 2+ points, have {count}"
    return True, f"{count} L2-valid pareto points"


def check_c4() -> tuple[bool, str]:
    events = _read_events(ROOT / "artifacts" / "swarm" / "event_log.jsonl")
    influenced = any(
        e.get("agent") == "Architect"
        and (e.get("payload") or {}).get("prompt_influenced")
        for e in events
    )
    exa_tags = any(
        e.get("agent") == "Memory"
        and any(str(t).startswith("exa:") for t in (e.get("payload") or {}).get("tags", []))
        for e in events
    )
    if not influenced:
        return False, "no Architect prompt_influenced events"
    if not exa_tags:
        return False, "no Memory record with exa: tags"
    return True, "research adoption visible on bus"


def check_c5() -> tuple[bool, str]:
    path = ROOT / "artifacts" / "measured_memory_ab.json"
    if not path.is_file():
        return False, "missing measured_memory_ab.json"
    data = _load_json(path)
    if "with_memory" not in data or "without_memory" not in data:
        return False, "memory A/B arms missing"
    return True, "memory A/B artifact on disk"


def check_c6() -> tuple[bool, str]:
    path = ROOT / "artifacts" / "verification_report.json"
    if not path.is_file():
        return False, "missing verification_report.json"
    return True, "L1–L5 verification report present"


def check_c7() -> tuple[bool, str]:
    events = _read_events(ROOT / "artifacts" / "swarm" / "event_log.jsonl")
    if not events:
        return False, "event log empty"
    agents_seen = {e.get("agent") for e in events}
    missing = [a for a in PIPELINE if a not in agents_seen]
    if missing:
        return False, f"pipeline missing agents: {missing}"
    return True, "full swarm pipeline in event_log.jsonl"


def check_c8() -> tuple[bool, str]:
    demo = _load_json(ROOT / "artifacts" / "demo_bundle.json")
    if demo.get("data_era") != "measured":
        return False, "demo_bundle must be measured-only"
    if not (ROOT / "demo" / "index.html").is_file():
        return False, "missing demo/index.html"
    return True, "demo bound to measured artifacts"


def check_c9() -> tuple[bool, str]:
    path = ROOT / "artifacts" / "measured_fifo_climb.json"
    if not path.is_file():
        return False, "missing measured_fifo_climb.json"
    data = _load_json(path)
    history = data.get("history", [])
    if len(history) < 1:
        return False, "FIFO climb history empty"
    return True, f"FIFO platform: {len(history)} measured step(s)"


def check_c10() -> tuple[bool, str]:
    import subprocess

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_demo_rehearsal.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, result.stdout.strip() or result.stderr.strip()
    return True, "demo rehearsal bundle complete"


CHECKS: list[tuple[str, str, callable]] = [
    ("C0", "Measured spine", check_c0),
    ("C1", "Architect climb", check_c1),
    ("C2", "Multi-step design loop", check_c2),
    ("C3", "Valid design frontier", check_c3),
    ("C4", "Research self-adoption", check_c4),
    ("C5", "Memory compounding", check_c5),
    ("C6", "Verification report", check_c6),
    ("C7", "Swarm event bus", check_c7),
    ("C8", "Visualization integrity", check_c8),
    ("C9", "FIFO platform proof", check_c9),
    ("C10", "Demo rehearsal", check_c10),
]


def main() -> int:
    failed: list[str] = []
    print("SPEC-v6.1 checkpoint validation")
    print("-" * 48)
    for cid, title, fn in CHECKS:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
        print(f"{cid} {title}: {status} — {detail}")
        if not ok:
            failed.append(cid)

    print("-" * 48)
    if failed:
        print(f"BLOCKED: {', '.join(failed)}")
        return 1
    print("ALL CHECKPOINTS PASS (C0–C10)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
