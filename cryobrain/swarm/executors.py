"""Tier-2 specialist executors (SPEC-v6 P-exec).

Thin wrappers around existing measured-loop APIs. Each call emits one bus event
and returns the underlying result. Executors accept optional precomputed
results so :func:`cryobrain.rl.proposal_loop.run_proposal_step` can keep a
single monkeypatchable ``score_fn`` boundary without re-running Verilator.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.grader.score import score_measured
from cryobrain.memory.models import MemoryRecord
from cryobrain.memory.store import MemoryStore
from cryobrain.retrieval.context_pack import ContextPack, build_context_pack
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.swarm.event_bus import Agent, EventBus, ROOT
from cryobrain.types import CryoBudget, DesignConfig, ScenarioConfig
from cryobrain.verify.l1_functional import run_l1
from cryobrain.verify.l4_synth import run_l4
from cryobrain.verify.l5_budget import run_l5

ScoreFn = Callable[[Path], dict[str, Any]]

MEASURED_DIR = ROOT / "artifacts" / "measured"
SCORES_DIR = ROOT / "artifacts" / "scores"


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _measurement_artifact_ref(design_id: str, measurement: dict[str, Any]) -> str:
    ref_path = MEASURED_DIR / f"{design_id}.json"
    return _write_json_artifact(ref_path, {"design_id": design_id, "measurement": measurement})


def _score_artifact_ref(design_id: str, score: dict[str, Any]) -> str:
    ref_path = SCORES_DIR / f"{design_id}.json"
    slim = {
        "design_id": design_id,
        "reward": score.get("reward"),
        "valid": score.get("valid"),
        "ler": score.get("ler"),
        "suppression": score.get("suppression"),
        "layers_passed": score.get("layers_passed"),
        "source": score.get("source"),
    }
    return _write_json_artifact(ref_path, slim)


def research_step(
    bus: EventBus,
    design_id: str,
    *,
    query: str | None = None,
    num_results: int = 5,
) -> ContextPack:
    """Exa context pack when available; otherwise empty priors."""
    if query:
        pack = build_context_pack(query, num_results=num_results)
    else:
        pack = build_context_pack(num_results=num_results)
    bus.emit(
        agent=Agent.RESEARCH,
        action="context_pack",
        design_id=design_id,
        payload={
            "query": pack.query,
            "hit_count": len(pack.hits),
            "urls": pack.urls,
        },
    )
    return pack


def architect_propose_step(
    bus: EventBus,
    design_id: str,
    design: DesignConfig,
    *,
    context_pack: ContextPack | None = None,
    prompt_influenced: bool = False,
) -> DesignConfig:
    """Emit Architect propose event for an already-selected DesignConfig."""
    payload = design.to_dict()
    if context_pack is not None and context_pack.hits:
        payload["research_pack_hash"] = hashlib.sha256(
            context_pack.prompt_block().encode()
        ).hexdigest()[:6]
        payload["prompt_influenced"] = prompt_influenced or bool(context_pack.urls)
    elif context_pack is not None and context_pack.urls:
        payload["prompt_influenced"] = prompt_influenced
    bus.emit(
        agent=Agent.ARCHITECT,
        action="propose",
        design_id=design_id,
        payload=payload,
    )
    return design


def rtl_generate_step(
    bus: EventBus,
    design_id: str,
    design: DesignConfig,
    rtl_dir: Path,
) -> Path:
    """Generate synthesizable RTL and emit RTL agent event."""
    rtl_path = generate_rtl(design, rtl_dir)
    bus.emit(
        agent=Agent.RTL,
        action="generate",
        design_id=design_id,
        payload={
            "rtl_path": str(rtl_path),
            "design": design.to_dict(),
        },
    )
    return rtl_path


def measure_step(
    bus: EventBus,
    design_id: str,
    rtl_path: Path,
    scenario: ScenarioConfig | dict[str, Any],
    *,
    measurement: dict[str, Any] | None = None,
    shots: int = 1000,
    seed: int = 1729,
) -> dict[str, Any]:
    """Run ``measure_candidate_ler`` (or replay a score sub-dict) and emit."""
    if isinstance(scenario, dict):
        scenario = ScenarioConfig.from_dict(scenario)
    result = dict(measurement) if measurement is not None else dict(
        measure_candidate_ler(rtl_path, scenario, shots=shots, seed=seed)
    )
    artifact_ref = _measurement_artifact_ref(design_id, result)
    bus.emit(
        agent=Agent.MEASUREMENT,
        action="measure",
        design_id=design_id,
        payload={
            "candidate_ler": float(result.get("candidate_ler", 1.0)),
            "mwpm_ler": float(result.get("mwpm_ler", 0.0)),
            "suppression": float(result.get("suppression", 0.0)),
            "rtl_valid": bool(result.get("rtl_valid", False)),
            "benchmark_vectors": int(result.get("benchmark_vectors", 0)),
        },
        measured=True,
        artifact_ref=artifact_ref,
    )
    return result


def verify_step(
    bus: EventBus,
    design_id: str,
    rtl_path: Path,
    *,
    budget: CryoBudget | dict[str, Any] | None = None,
    layers_passed: list[str] | None = None,
) -> dict[str, Any]:
    """Run L1/L4/L5 gates (L3 stub) and emit Verifier event."""
    if layers_passed is not None:
        l1 = {"passed": "L1" in layers_passed}
        l4 = {"passed": "L4" in layers_passed}
        l5 = {"passed": "L5" in layers_passed}
        l3 = {"passed": False, "skipped": True, "reason": "L3 formal pending (SPEC-v6)"}
        passed_layers = list(layers_passed)
    else:
        l1 = run_l1(rtl_path)
        l3 = {"passed": False, "skipped": True, "reason": "L3 formal pending (SPEC-v6)"}
        l4 = run_l4(rtl_path)
        if isinstance(budget, dict):
            budget = CryoBudget.from_dict(budget)
        budget = budget or CryoBudget()
        l5 = run_l5(rtl_path, budget=budget)
        passed_layers = []
        if l1["passed"]:
            passed_layers.append("L1")
        if l4["passed"]:
            passed_layers.append("L4")
        if l5["passed"]:
            passed_layers.append("L5")

    payload = {
        "layers_passed": passed_layers,
        "l1": l1,
        "l3": l3,
        "l4": l4,
        "l5": l5,
        "all_gates_passed": {"L1", "L4", "L5"}.issubset(set(passed_layers)),
    }
    bus.emit(
        agent=Agent.VERIFIER,
        action="verify",
        design_id=design_id,
        payload=payload,
    )
    return payload


def score_step(
    bus: EventBus,
    design_id: str,
    workdir: Path,
    *,
    score_fn: ScoreFn = score_measured,
    score: dict[str, Any] | None = None,
    shots: int = 1000,
    seed: int = 1729,
    emit: bool = True,
) -> dict[str, Any]:
    """Score via ``score_measured`` (or replay) and emit Scorer event."""
    result = dict(score) if score is not None else dict(score_fn(workdir))
    if emit:
        valid = bool(result.get("valid", False))
        artifact_ref = _score_artifact_ref(design_id, result) if valid else None
        bus.emit(
            agent=Agent.SCORER,
            action="score",
            design_id=design_id,
            payload={
                "reward": float(result.get("reward", 0.0)),
                "valid": valid,
                "ler": float(result.get("ler", 1.0)),
                "suppression": float(result.get("suppression", 0.0)),
                "layers_passed": list(result.get("layers_passed", [])),
            },
            measured=valid,
            artifact_ref=artifact_ref,
        )
    return result


def memory_step(
    bus: EventBus,
    design_id: str,
    store: MemoryStore,
    record: MemoryRecord,
    *,
    memory_tags: list[str] | None = None,
) -> str:
    """Persist a measured variant and emit Memory event."""
    rtl_hash = store.record_variant(record)
    tags = memory_tags if memory_tags is not None else list(record.provenance.tags)
    payload: dict[str, Any] = {
        "rtl_hash": rtl_hash,
        "rtl_path": record.rtl_path,
        "candidate_ler": record.measurement.candidate_ler,
        "verification_passed": record.verification.passed,
    }
    if tags:
        payload["tags"] = tags
    bus.emit(
        agent=Agent.MEMORY,
        action="record_variant",
        design_id=design_id,
        payload=payload,
    )
    return rtl_hash