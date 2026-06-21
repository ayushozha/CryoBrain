"""Export SPEC-v6.1 checkpoint artifacts: design_runs/ + verification_report.json."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
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
    "Architect",
    "RTL",
    "Measurement",
    "Verifier",
    "Scorer",
    "Memory",
)


def _load_scenario() -> dict:
    return json.loads((TASK_ROOT / "scenario.json").read_text(encoding="utf-8"))


def _events_by_design(log_path: Path) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    if not log_path.is_file():
        return grouped
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        grouped[str(event.get("design_id", ""))].append(event)
    return grouped


def _first_event(events: list[dict], agent: str, action: str | None = None) -> dict | None:
    for event in events:
        if event.get("agent") != agent:
            continue
        if action is not None and event.get("action") != action:
            continue
        return event
    return None


def export_design_runs(*, log_path: Path = DEFAULT_LOG, limit: int = 3) -> list[str]:
    """Materialize design_runs/<id>/ bundles from the swarm event log."""
    grouped = _events_by_design(log_path)
    design_ids = sorted(grouped.keys())[:limit]
    exported: list[str] = []

    for design_id in design_ids:
        events = grouped[design_id]
        if not _first_event(events, "Measurement", "measure"):
            continue

        out_dir = DESIGN_RUNS / design_id
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        research = _first_event(events, "Research", "context_pack")
        if research:
            (out_dir / "research_context.json").write_text(
                json.dumps(research.get("payload", {}), indent=2) + "\n",
                encoding="utf-8",
            )

        architect = _first_event(events, "Architect", "propose")
        if architect:
            (out_dir / "design_config.json").write_text(
                json.dumps(architect.get("payload", {}), indent=2) + "\n",
                encoding="utf-8",
            )

        rtl = _first_event(events, "RTL", "generate")
        rtl_src = (rtl or {}).get("payload", {}).get("rtl_path")
        if rtl_src and Path(rtl_src).is_file():
            shutil.copy2(rtl_src, out_dir / "generated_decoder.sv")
        else:
            design_payload = (architect or {}).get("payload", {})
            if design_payload:
                from cryobrain.types import DesignConfig

                workdir = out_dir / "_gen"
                generate_rtl(DesignConfig.from_dict(design_payload), workdir)
                shutil.copy2(workdir / "cryo_brain_decoder.sv", out_dir / "generated_decoder.sv")

        for agent, action, filename in (
            ("Measurement", "measure", "stim_ler_result.json"),
            ("Verifier", "verify", "verilator_result.json"),
            ("Scorer", "score", "score.json"),
            ("Memory", "record_variant", "memory_update.json"),
        ):
            hit = _first_event(events, agent, action)
            if hit:
                (out_dir / filename).write_text(
                    json.dumps(hit.get("payload", {}), indent=2) + "\n",
                    encoding="utf-8",
                )
                if hit.get("artifact_ref"):
                    src = ROOT / str(hit["artifact_ref"])
                    if src.is_file():
                        shutil.copy2(src, out_dir / Path(hit["artifact_ref"]).name)

        pipeline = [e for e in events if e.get("agent") in PIPELINE_AGENTS]
        (out_dir / "plan.json").write_text(
            json.dumps({"design_id": design_id, "pipeline_events": len(pipeline)}, indent=2) + "\n",
            encoding="utf-8",
        )
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
        VERIFICATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
        VERIFICATION_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return VERIFICATION_REPORT

    VERIFICATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path, VERIFICATION_REPORT)
    return VERIFICATION_REPORT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design-runs", type=int, default=3, help="Number of design cycles to export")
    parser.add_argument("--skip-verification", action="store_true")
    args = parser.parse_args()

    exported = export_design_runs(limit=args.design_runs)
    print(f"design_runs exported: {exported}")

    if not args.skip_verification:
        try:
            path = export_verification_report()
            print(f"verification_report: {path}")
        except Exception as exc:  # noqa: BLE001 — CLI fallback for Windows without EDA
            write_verification_report_template(ROOT)
            print(f"verification_report template (EDA unavailable: {exc}): {VERIFICATION_REPORT}")


if __name__ == "__main__":
    main()