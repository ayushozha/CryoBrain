"""Export SPEC-v6.1 checkpoint artifacts: design_runs/ + verification_report.json."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from cryobrain.artifacts.verification_report import (
    build_verification_report,
    write_verification_report_template,
)
from cryobrain.calibration.cp3 import stage_workdir
from cryobrain.design.config import GOLDEN_BASELINE
from cryobrain.grader.score import score_measured
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.swarm.event_bus import DEFAULT_LOG

ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "tasks" / "cryo_brain_decoder"
DESIGN_RUNS = ROOT / "artifacts" / "design_runs"
VERIFICATION_REPORT = ROOT / "artifacts" / "verification_report.json"

PIPELINE_AGENTS = (
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


def _load_scenario() -> dict:
    return json.loads((TASK_ROOT / "scenario.json").read_text(encoding="utf-8"))


def _read_events(log_path: Path) -> list[dict]:
    if not log_path.is_file():
        return []
    events: list[dict] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def _event_runs(log_path: Path) -> list[list[dict]]:
    runs: list[list[dict]] = []
    pending_plans: dict[str, dict] = {}
    current: list[dict] | None = None

    for event in _read_events(log_path):
        design_id = str(event.get("design_id", ""))
        agent = event.get("agent")
        action = event.get("action")
        if agent == "Planner" and action == "plan":
            pending_plans[design_id] = event
            continue
        if agent == "Research" and action == "context_pack":
            if current and _has_measure_and_score(current):
                runs.append(current)
            current = []
            if design_id in pending_plans:
                current.append(pending_plans.pop(design_id))
            current.append(event)
            continue
        if current is not None:
            current.append(event)

    if current and _has_measure_and_score(current):
        runs.append(current)
    return runs


def _has_measure_and_score(events: list[dict]) -> bool:
    return bool(_first_event(events, "Measurement", "measure") and _first_event(events, "Scorer", "score"))


def _first_event(events: list[dict], agent: str, action: str | None = None) -> dict | None:
    for event in events:
        if event.get("agent") != agent:
            continue
        if action is not None and event.get("action") != action:
            continue
        return event
    return None


def _last_event(events: list[dict], agent: str, action: str | None = None) -> dict | None:
    for event in reversed(events):
        if event.get("agent") != agent:
            continue
        if action is not None and event.get("action") != action:
            continue
        return event
    return None


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _artifact_path(ref: str | None) -> Path | None:
    if not ref:
        return None
    path = Path(str(ref))
    if not path.is_absolute():
        path = ROOT / path
    try:
        rel = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    allowed = (Path("artifacts") / "measured", Path("artifacts") / "scores")
    if len(rel.parts) < 3 or Path(*rel.parts[:2]) not in allowed:
        return None
    return path


def _artifact_payload(ref: str | None) -> dict:
    src = _artifact_path(ref)
    if src is None:
        return {}
    if not src.is_file():
        return {}
    try:
        return json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _copy_artifact_ref(ref: str | None, out_dir: Path) -> None:
    src = _artifact_path(ref)
    if src is not None and src.is_file():
        shutil.copy2(src, out_dir / src.name)


def _assert_verification_green(report: dict) -> None:
    if not bool(report.get("all_passed")):
        raise RuntimeError("verification_report all_passed=false")


def _consistent_measurement_score(measurement: dict, score: dict) -> bool:
    if not measurement or not score:
        return False
    score_measurement = score.get("measurement") if isinstance(score.get("measurement"), dict) else {}
    checks = (
        ("candidate_ler", score.get("ler")),
        ("suppression", score.get("suppression")),
    )
    for measurement_key, score_value in checks:
        if measurement_key in measurement and score_value is not None:
            if float(measurement[measurement_key]) != float(score_value):
                return False
        if measurement_key in measurement and measurement_key in score_measurement:
            if float(measurement[measurement_key]) != float(score_measurement[measurement_key]):
                return False
    return True


def _run_summary(design_id: str, events: list[dict], out_dir: Path) -> str:
    score = json.loads((out_dir / "score.json").read_text(encoding="utf-8"))
    measurement = json.loads((out_dir / "stim_ler_result.json").read_text(encoding="utf-8"))
    research = json.loads((out_dir / "research_context.json").read_text(encoding="utf-8"))
    valid = bool(score.get("valid"))
    reward = score.get("reward")
    ler = measurement.get("candidate_ler")
    suppression = measurement.get("suppression")
    urls = research.get("urls") or []
    agents = " -> ".join(e.get("agent", "?") for e in events if e.get("agent") in PIPELINE_AGENTS)
    return (
        f"# Design Run {design_id}\n\n"
        f"- Valid: {valid}\n"
        f"- Reward: {reward}\n"
        f"- Candidate LER: {ler}\n"
        f"- Suppression: {suppression}\n"
        f"- Research URLs: {len(urls)}\n"
        f"- Pipeline: {agents}\n"
    )


def export_design_runs(*, log_path: Path = DEFAULT_LOG, limit: int = 5) -> list[str]:
    """Materialize design_runs/<id>/ bundles from the swarm event log."""
    runs = _event_runs(log_path)
    selected = [events for events in runs if _has_measure_and_score(events)][-limit:]
    exported: list[str] = []

    for idx, events in enumerate(selected):
        design_id = f"d{idx:03d}"
        source_design_id = str(events[0].get("design_id", design_id))

        out_dir = DESIGN_RUNS / design_id
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        research = _first_event(events, "Research", "context_pack")
        _write_json(out_dir / "research_context.json", (research or {}).get("payload", {}))

        architect = _first_event(events, "Architect", "propose")
        design_payload = (architect or {}).get("payload", {})
        _write_json(out_dir / "design_config.json", design_payload)

        rtl = _first_event(events, "RTL", "generate")
        rtl_src = (rtl or {}).get("payload", {}).get("rtl_path")
        if rtl_src and Path(rtl_src).is_file():
            shutil.copy2(rtl_src, out_dir / "generated_decoder.sv")
        else:
            if design_payload:
                from cryobrain.types import DesignConfig

                workdir = out_dir / "_gen"
                try:
                    generate_rtl(DesignConfig.from_dict(design_payload), workdir)
                    shutil.copy2(workdir / "cryo_brain_decoder.sv", out_dir / "generated_decoder.sv")
                finally:
                    shutil.rmtree(workdir, ignore_errors=True)

        measurement = _first_event(events, "Measurement", "measure")
        measurement_payload = (measurement or {}).get("payload", {})
        _write_json(out_dir / "stim_ler_result.json", measurement_payload)
        _write_json(out_dir / "verilator_result.json", measurement_payload)
        if measurement:
            _copy_artifact_ref(measurement.get("artifact_ref"), out_dir)

        scorer = _last_event(events, "Scorer", "score")
        score_artifact_payload = _artifact_payload((scorer or {}).get("artifact_ref"))
        score_payload = score_artifact_payload or (scorer or {}).get("payload", {})
        source_score_design_id = score_payload.get("design_id", source_design_id)
        score_payload = {
            **score_payload,
            "design_id": design_id,
            "source_design_id": source_score_design_id,
        }
        if not _consistent_measurement_score(measurement_payload, score_payload):
            raise RuntimeError(f"{design_id} has inconsistent measurement and score payloads")
        _write_json(out_dir / "score.json", score_payload)
        if scorer:
            _copy_artifact_ref(scorer.get("artifact_ref"), out_dir)

        synth = score_payload.get("synth") or {
            "area_um2": score_payload.get("area_um2"),
            "latency_cycles": score_payload.get("latency_cycles"),
            "power_mw_est": score_payload.get("power_mw"),
        }
        _write_json(out_dir / "yosys_metrics.json", synth)

        verifier = _first_event(events, "Verifier", "verify")
        verify_payload = (verifier or {}).get("payload", {}) or {
            "layers_passed": score_payload.get("layers_passed", []),
            "valid": score_payload.get("valid", False),
            "design_id": design_id,
        }
        verify_payload = {
            **verify_payload,
            "design_id": design_id,
            "source_design_id": verify_payload.get("design_id", source_design_id),
        }
        _write_json(out_dir / "verification_report.json", verify_payload)

        memory = _last_event(events, "Memory", "record_variant")
        _write_json(out_dir / "memory_update.json", (memory or {}).get("payload", {}))

        pipeline = [e for e in events if e.get("agent") in PIPELINE_AGENTS]
        planner = _first_event(events, "Planner", "plan")
        _write_json(
            out_dir / "plan.json",
            {
                "design_id": design_id,
                "source_design_id": source_design_id,
                "pipeline_events": len(pipeline),
                "planner": (planner or {}).get("payload", {}),
            },
        )
        (out_dir / "run_summary.md").write_text(_run_summary(design_id, pipeline, out_dir), encoding="utf-8")
        missing = [name for name in MANDATORY_RUN_FILES if not (out_dir / name).is_file()]
        if missing:
            raise RuntimeError(f"{design_id} export missing mandatory files: {missing}")
        exported.append(design_id)

    return exported


def export_verification_report() -> Path:
    """Run golden baseline through score_measured and write artifacts/verification_report.json."""
    scenario = _load_scenario()
    workdir = stage_workdir(TASK_ROOT, scenario=scenario, design=GOLDEN_BASELINE.to_dict())
    generate_rtl(GOLDEN_BASELINE, workdir / "rtl")
    score = score_measured(workdir, emit_verification_report=True)
    report_path = workdir / "artifacts" / "verification_report.json"
    if not report_path.is_file():
        report = build_verification_report(
            rtl_path=workdir / "rtl" / "cryo_brain_decoder.sv",
            l1={"passed": "L1" in score.get("layers_passed", [])},
            l2_measure=score.get("measurement"),
            l3={"passed": False, "skipped": True, "reason": "sby not on PATH"},
            l4={"passed": "L4" in score.get("layers_passed", [])},
            l5={"passed": "L5" in score.get("layers_passed", [])},
        )
        _assert_verification_green(report)
        VERIFICATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
        VERIFICATION_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return VERIFICATION_REPORT

    report = json.loads(report_path.read_text(encoding="utf-8"))
    _assert_verification_green(report)
    VERIFICATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path, VERIFICATION_REPORT)
    return VERIFICATION_REPORT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design-runs", type=int, default=5, help="Number of design cycles to export")
    parser.add_argument("--skip-verification", action="store_true")
    parser.add_argument("--allow-verification-template", action="store_true")
    args = parser.parse_args()

    exported = export_design_runs(limit=args.design_runs)
    print(f"design_runs exported: {exported}")

    if not args.skip_verification:
        try:
            path = export_verification_report()
            print(f"verification_report: {path}")
        except Exception as exc:  # noqa: BLE001 — CLI fallback for Windows without EDA
            if not args.allow_verification_template:
                raise
            write_verification_report_template(ROOT)
            print(f"verification_report template (EDA unavailable: {exc}): {VERIFICATION_REPORT}")


if __name__ == "__main__":
    main()
