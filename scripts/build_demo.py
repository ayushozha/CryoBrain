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
from cryobrain.swarm.visualization import build_swarm_timeline  # noqa: E402

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


def _normalize_measured_climb(measured: dict) -> dict:
    """Adapt measured_climb.json for the dashboard reward chart."""
    rows = measured.get("history") or []
    history = [
        {
            "step": row["step"],
            "reward": float(row["suppression"]),
            "candidate_ler": float(row.get("candidate_ler", 0.0)),
            "suppression": float(row.get("suppression", 0.0)),
            "rtl_hash": row.get("rtl_hash"),
        }
        for row in rows
        if isinstance(row, dict) and "step" in row and "suppression" in row
    ]
    out: dict = {
        "target": measured.get("target", "cryo_brain_decoder"),
        "backend": measured.get("backend", "measured"),
        "reward_source": measured.get("reward_source", "score_measured"),
        "history": history,
    }
    if history:
        out["summary"] = {
            "start_reward": history[0]["reward"],
            "end_reward": history[-1]["reward"],
            "steps": len(history),
        }
    return out


def _normalize_fifo_climb(measured: dict) -> dict | None:
    """Adapt measured_fifo_climb.json for the dashboard improvement chart."""
    rows = measured.get("history") or []
    history = [
        {
            "step": row["step"],
            "reward": float(row["suppression"]),
            "throughput": float(row.get("throughput", 0.0)),
            "suppression": float(row.get("suppression", 0.0)),
            "rtl_hash": row.get("rtl_hash"),
        }
        for row in rows
        if isinstance(row, dict) and "step" in row and "throughput" in row
    ]
    if not history:
        return None
    start_tp = history[0]["throughput"]
    end_tp = history[-1]["throughput"]
    return {
        "target": measured.get("target", "stream_arb_fifo"),
        "backend": measured.get("backend", "verilator+fifo-throughput"),
        "reward_source": measured.get("reward_source", "measured_fifo_throughput"),
        "metric": "throughput",
        "history": history,
        "summary": {
            "start_throughput": start_tp,
            "end_throughput": end_tp,
            "start_reward": history[0]["reward"],
            "end_reward": history[-1]["reward"],
            "steps": len(history),
            "delta_throughput": round(end_tp - start_tp, 6),
        },
    }


def _improvement_summary(climb: dict | None, fifo: dict | None, pareto_count: int) -> dict:
    """Honest one-glance improvement stats for the demo strip."""
    tracks: list[dict] = []
    if isinstance(climb, dict) and climb.get("history"):
        summary = climb.get("summary") or {}
        start = float(summary.get("start_reward", climb["history"][0]["reward"]))
        end = float(summary.get("end_reward", climb["history"][-1]["reward"]))
        steps = int(summary.get("steps", len(climb["history"])))
        tracks.append(
            {
                "target": climb.get("target", "cryo_brain_decoder"),
                "metric": "suppression",
                "steps": steps,
                "start": round(start, 4),
                "end": round(end, 4),
                "improving": end > start and steps >= 2,
                "note": "multi-step climb" if steps >= 2 and end > start else "golden baseline",
            }
        )
    if isinstance(fifo, dict) and fifo.get("history"):
        summary = fifo.get("summary") or {}
        start_tp = float(summary.get("start_throughput", fifo["history"][0]["throughput"]))
        end_tp = float(summary.get("end_throughput", fifo["history"][-1]["throughput"]))
        steps = int(summary.get("steps", len(fifo["history"])))
        tracks.append(
            {
                "target": fifo.get("target", "stream_arb_fifo"),
                "metric": "throughput",
                "steps": steps,
                "start": round(start_tp, 4),
                "end": round(end_tp, 4),
                "improving": end_tp > start_tp and steps >= 2,
                "note": f"+{round(end_tp - start_tp, 3)} measured throughput",
            }
        )
    best_story = "fifo" if any(t.get("target") == "stream_arb_fifo" and t.get("improving") for t in tracks) else "decoder"
    return {
        "tracks": tracks,
        "pareto_points": pareto_count,
        "headline_target": best_story,
        "agents_keep_improving": any(t.get("improving") for t in tracks),
    }


def _memory_from_measured(ab: dict) -> dict | None:
    """Adapt measured_memory_ab.json to the dashboard memory overlay shape."""

    def _side(rows: list | None) -> dict | None:
        if not isinstance(rows, list) or not rows:
            return None
        history = [
            {"step": row["step"], "reward": float(row["suppression"])}
            for row in rows
            if isinstance(row, dict) and "step" in row and "suppression" in row
        ]
        if not history:
            return None
        return {
            "end_reward": history[-1]["reward"],
            "slope": round(_slope(history), 6),
            "history": history,
        }

    without = _side(ab.get("without_memory"))
    with_side = _side(ab.get("with_memory"))
    if not without or not with_side:
        return None

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
        reward = float(row.get("reward", 0.0))
        fits = (
            reward > 0
            if reward > 0
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
                "reward": reward,
                "is_winner": name == best_name,
            }
        )
    return points


def _pareto_from_measured(measured: dict) -> list[dict]:
    raw_points = measured.get("points") or []
    if not isinstance(raw_points, list):
        return []

    candidates = [p for p in raw_points if isinstance(p, dict) and p.get("ler") is not None]
    if not candidates:
        return []

    frontier = [p for p in candidates if p.get("on_frontier")]
    pool = frontier or candidates
    best = min(pool, key=lambda p: (float(p["ler"]), float(p.get("area_um2", 0.0))))
    best_label = str(best.get("label", ""))
    max_area_um2 = BUDGET["max_area_mm2"] * 1_000_000

    points: list[dict] = []
    for row in candidates:
        label = str(row.get("label", "design"))
        ler = float(row["ler"])
        area_um2 = float(row.get("area_um2", 0.0))
        latency = int(row.get("latency_cycles", 12) or 12)
        suppression = max(0.0, 1.0 - ler / MWPM_LER) if MWPM_LER else 0.0
        points.append(
            {
                "label": label,
                "kind": "policy",
                "ler": round(ler, 6),
                "area_um2": round(area_um2, 3),
                "latency_cycles": latency,
                "power_mw": 0.0,
                "fits_budget": latency <= BUDGET["max_latency_cycles"] and area_um2 <= max_area_um2,
                "reward": round(suppression, 6),
                "is_winner": label == best_label,
            }
        )
    return points


class MissingMeasuredArtifactsError(RuntimeError):
    """Raised when required measured artifacts are absent (no proxy fallback)."""


def _require_measured_climb(artifacts: Path) -> tuple[dict, str]:
    measured = _load(artifacts / "measured_climb.json")
    if not isinstance(measured, dict) or not measured.get("history"):
        raise MissingMeasuredArtifactsError(
            "artifacts/measured_climb.json with non-empty history is required "
            "(run scripts/run_c5_climb_wsl.sh in WSL)"
        )
    return _normalize_measured_climb(measured), "artifacts/measured_climb.json"


def _require_measured_memory(artifacts: Path) -> tuple[dict, str]:
    measured = _load(artifacts / "measured_memory_ab.json")
    memory = _memory_from_measured(measured) if isinstance(measured, dict) else None
    if not memory:
        raise MissingMeasuredArtifactsError(
            "artifacts/measured_memory_ab.json is required "
            "(run scripts/run_memory_ab_wsl.sh in WSL)"
        )
    return memory, "artifacts/measured_memory_ab.json"


def _require_measured_pareto(artifacts: Path) -> tuple[list[dict], str]:
    measured = _load(artifacts / "measured_pareto.json")
    if not isinstance(measured, dict) or not measured.get("points"):
        raise MissingMeasuredArtifactsError(
            "artifacts/measured_pareto.json with points is required "
            "(produced by measured climb / pareto export)"
        )
    return _pareto_from_measured(measured), "artifacts/measured_pareto.json"


def _load_fifo_climb(artifacts: Path) -> tuple[dict | None, str]:
    measured = _load(artifacts / "measured_fifo_climb.json")
    fifo = _normalize_fifo_climb(measured) if isinstance(measured, dict) else None
    source = "artifacts/measured_fifo_climb.json" if fifo else ""
    return fifo, source


def build_bundle(artifacts_dir: Path | None = None, *, require_measured: bool = True) -> dict:
    artifacts = artifacts_dir or ARTIFACTS
    vcd = artifacts / "cryo_golden_trace.vcd"
    waveform = write_waveform_json(vcd, artifacts / "waveform.json") if vcd.is_file() else None

    if require_measured:
        climb, climb_source = _require_measured_climb(artifacts)
        memory, memory_source = _require_measured_memory(artifacts)
        pareto, pareto_source = _require_measured_pareto(artifacts)
        fifo, fifo_source = _load_fifo_climb(artifacts)
        climb_era = memory_era = pareto_era = "measured"
        fifo_era = "measured" if fifo else "missing"
    else:
        measured_climb = _load(artifacts / "measured_climb.json")
        climb = (
            _normalize_measured_climb(measured_climb)
            if isinstance(measured_climb, dict) and measured_climb.get("history")
            else None
        )
        climb_source = "artifacts/measured_climb.json" if climb else ""
        climb_era = "measured" if climb else "missing"

        measured_memory = _load(artifacts / "measured_memory_ab.json")
        memory = _memory_from_measured(measured_memory) if isinstance(measured_memory, dict) else None
        memory_source = "artifacts/measured_memory_ab.json" if memory else ""
        memory_era = "measured" if memory else "missing"

        measured_pareto = _load(artifacts / "measured_pareto.json")
        pareto = (
            _pareto_from_measured(measured_pareto)
            if isinstance(measured_pareto, dict) and measured_pareto.get("points")
            else []
        )
        pareto_source = "artifacts/measured_pareto.json" if pareto else ""
        pareto_era = "measured" if pareto else "missing"

        fifo, fifo_source = _load_fifo_climb(artifacts)
        fifo_era = "measured" if fifo else "missing"

    cp5_audit = _load(artifacts / "cp5_audit.json")
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

    swarm_timeline = build_swarm_timeline(artifacts / "swarm" / "event_log.jsonl")

    if require_measured:
        data_era = "measured"
    else:
        eras = {climb_era, memory_era, pareto_era} - {"missing"}
        data_era = "measured" if eras == {"measured"} else ("mixed" if eras else "missing")

    pareto_count = len(pareto) if isinstance(pareto, list) else 0

    return {
        "data_era": data_era,
        "waveform": waveform,
        "climb": climb,
        "fifo_climb": fifo,
        "improvement": _improvement_summary(climb, fifo, pareto_count),
        "memory": memory,
        "pareto": {"budget": BUDGET, "yosys_area_um2": yosys_area_um2, "points": pareto},
        "gate": gate,
        "swarm_timeline": swarm_timeline,
        "sources": {
            "waveform": "artifacts/waveform.json",
            "climb": climb_source,
            "fifo_climb": fifo_source,
            "memory": memory_source,
            "pareto": pareto_source,
            "gate": "CP2 validity gate",
            "climb_era": climb_era,
            "fifo_era": fifo_era,
            "memory_era": memory_era,
            "pareto_era": pareto_era,
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