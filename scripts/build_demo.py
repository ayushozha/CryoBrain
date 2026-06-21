#!/usr/bin/env python3
"""Bundle real artifacts into offline demo/index.html (SPEC4 / dashboardspec)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
DEMO = ROOT / "demo"
sys.path.insert(0, str(ROOT))

from cryobrain.demo.vcd_export import write_waveform_json  # noqa: E402

MWPM_LER = 0.022
BUDGET = {
    "max_latency_cycles": 64,
    "max_area_mm2": 0.06,
    "max_power_mw": 8.0,
}


def _load(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _slope(history: list[dict]) -> float:
    if len(history) < 2:
        return 0.0
    start = float(history[0].get("reward", 0.0))
    end = float(history[-1].get("reward", 0.0))
    return (end - start) / max(len(history) - 1, 1)


def _memory_overlay(
    no_mem: dict | None,
    with_mem: dict | None,
    overlay: dict | None,
) -> dict | None:
    if not isinstance(no_mem, dict) or not isinstance(with_mem, dict):
        return None
    no_hist = no_mem.get("history", [])
    mem_hist = with_mem.get("history", [])
    if not no_hist or not mem_hist:
        return None
    if float(no_hist[-1].get("reward", 0)) <= 0 and float(mem_hist[-1].get("reward", 0)) <= 0:
        return None

    without = {
        "end_reward": float(
            (overlay or {}).get("without_memory", {}).get("end_reward")
            or no_mem.get("summary", {}).get("end_reward", no_hist[-1]["reward"])
        ),
        "slope": round(
            float((overlay or {}).get("without_memory", {}).get("slope", _slope(no_hist))),
            6,
        ),
        "history": [{"step": h["step"], "reward": h["reward"]} for h in no_hist],
    }
    with_side = {
        "end_reward": float(
            (overlay or {}).get("with_memory", {}).get("end_reward")
            or with_mem.get("summary", {}).get("end_reward", mem_hist[-1]["reward"])
        ),
        "slope": round(
            float((overlay or {}).get("with_memory", {}).get("slope", _slope(mem_hist))),
            6,
        ),
        "history": [{"step": h["step"], "reward": h["reward"]} for h in mem_hist],
        "memory_records": int(
            (overlay or {}).get("with_memory", {}).get("memory_records")
            or with_mem.get("memory_records", 0)
        ),
    }
    rebuilt = {
        "ok": True,
        "without_memory": without,
        "with_memory": with_side,
        "memory_wins": with_side["end_reward"] >= without["end_reward"],
    }
    if without["slope"] > 0:
        rebuilt["slope_ratio"] = round(with_side["slope"] / without["slope"], 2)
    else:
        rebuilt["slope_ratio"] = None
    return rebuilt


def _pareto_points(designs: list | None) -> list[dict]:
    if not isinstance(designs, list):
        return []
    points: list[dict] = []
    best_name = None
    best_reward = -1.0
    for row in designs:
        if not isinstance(row, dict) or row.get("kind") != "policy":
            continue
        reward = float(row.get("reward", 0.0))
        if reward > best_reward and not row.get("hard_caps"):
            best_reward = reward
            best_name = row.get("name")

    for row in designs:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "design"))
        suppression = float(row.get("ler_suppression", 0.0))
        ler = round(MWPM_LER * max(0.0, 1.0 - suppression), 6)
        area_mm2 = float(row.get("area_mm2", 0.0))
        latency = int(row.get("latency_cycles", row.get("latency", 0)) or 0)
        hard = list(row.get("hard_caps") or [])
        fits = (
            reward > 0
            if (reward := float(row.get("reward", 0.0))) > 0
            else not hard
            and latency <= BUDGET["max_latency_cycles"]
            and area_mm2 <= BUDGET["max_area_mm2"]
        )
        if name == "mwpm":
            fits = False
        points.append(
            {
                "label": name,
                "kind": row.get("kind", "policy"),
                "ler": ler,
                "area_um2": round(area_mm2 * 1_000_000, 3),
                "latency_cycles": latency or 12,
                "power_mw": float(row.get("power_mw", 0.0)),
                "fits_budget": bool(fits and not hard),
                "reward": float(row.get("reward", 0.0)),
                "is_winner": name == best_name,
            }
        )
    return points


def build_bundle() -> dict:
    vcd = ARTIFACTS / "cryo_golden_trace.vcd"
    waveform = write_waveform_json(vcd, ARTIFACTS / "waveform.json") if vcd.is_file() else None

    climb = _load(ARTIFACTS / "climb_chart_rl.json") or _load(ARTIFACTS / "climb_chart.json")
    no_mem = _load(ARTIFACTS / "climb_chart_no_memory.json")
    with_mem = _load(ARTIFACTS / "climb_chart_memory.json")
    memory = _memory_overlay(no_mem, with_mem, _load(ARTIFACTS / "memory_ab_overlay.json"))

    designs = _load(ARTIFACTS / "designs.json") or _load(ARTIFACTS / "designs_rl.json")
    pareto = _pareto_points(designs if isinstance(designs, list) else None)

    cp5_audit = _load(ARTIFACTS / "cp5_audit.json")
    yosys_area_um2 = 6.0
    if isinstance(cp5_audit, dict):
        yosys_area_um2 = float(cp5_audit.get("area_estimate_um2", yosys_area_um2))

    gate = {
        "invalid": {"label": "invalid decoder", "reward": 0.0},
        "valid": {"label": "verified starter", "reward": None},
        "golden": {"label": "golden reference", "reward": None},
    }
    if isinstance(climb, dict) and climb.get("summary"):
        gate["valid"]["reward"] = float(climb["summary"].get("start_reward", 0.0))

    gate_path = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "grade_calibration.json"
    if gate_path.is_file():
        cal = json.loads(gate_path.read_text(encoding="utf-8"))
        gate["golden"]["reward"] = float(cal.get("golden_reward", 0.629))

    return {
        "waveform": waveform,
        "climb": climb,
        "memory": memory,
        "pareto": {"budget": BUDGET, "yosys_area_um2": yosys_area_um2, "points": pareto},
        "gate": gate,
        "sources": {
            "waveform": "artifacts/waveform.json",
            "climb": "artifacts/climb_chart_rl.json",
            "memory": "artifacts/memory_ab_overlay.json",
            "pareto": "artifacts/designs.json",
            "gate": "CP2 validity gate",
        },
    }


def render_html(bundle: dict) -> str:
    data_json = json.dumps(bundle, separators=(",", ":"))
    template = (DEMO / "dashboard.template.html").read_text(encoding="utf-8")
    return template.replace("/*__DEMO_DATA__*/", data_json)


def main() -> None:
    DEMO.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle()
    (ARTIFACTS / "demo_bundle.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    html = render_html(bundle)
    (DEMO / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(DEMO / "index.html"), "bundle": str(ARTIFACTS / "demo_bundle.json")}, indent=2))


if __name__ == "__main__":
    main()