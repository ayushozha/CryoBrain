"""Measured proposal step (SPEC-v5 C5 / MP3, SPEC-v6 P-exec).

The single reusable unit of the measured loop. One ``run_proposal_step`` does:

    research -> propose DesignConfig -> generate_rtl -> [verify + measure + score] -> memory

Tier-2 executor steps emit to the swarm event bus (SPEC-v6 §2) in pipeline order.

The bracketed middle is **one measured boundary**: Grok's
:func:`cryobrain.grader.score.score_measured`. It already runs the L1/L4/L5
verification gates, ``measure_candidate_ler`` (Stim->Verilator real LER), and
``synth_metrics`` (Yosys), and zeroes the reward when verification fails. We do
NOT reimplement any of those — we drive ``score_measured`` and thread its
measured output into reward + memory.

This module is also the reward boundary C4 (GRPO) consumes: ``measured_reward``
takes a ``DesignConfig`` and returns the measured reward (plus the full score
dict), with verification failure => reward 0.0. There is **no proxy/formula**
reward anywhere here.

Windows note: the real measured path needs Verilator + Yosys (Linux-only). On
Windows the EDA tools are absent, so ``score_measured`` returns an invalid /
zero-reward result for a generated variant; the end-to-end climb runs in WSL
(``scripts/run_c5_climb_wsl.sh``). The unit test monkeypatches ``score_measured``
to exercise the wiring without EDA.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from cryobrain.calibration.cp3 import stage_workdir
from cryobrain.grader.score import score_measured
from cryobrain.memory.models import MemoryRecord, Verification
from cryobrain.memory.store import MemoryStore, rtl_hash
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.swarm.event_bus import EventBus
from cryobrain.swarm.executors import (
    architect_propose_step,
    measure_step,
    memory_step,
    research_step,
    rtl_generate_step,
    score_step,
    verify_step,
)
from cryobrain.retrieval.context_pack import ContextPack
from cryobrain.types import CryoBudget, DesignConfig

ROOT = Path(__file__).resolve().parents[2]
TASK_ROOT = ROOT / "tasks" / "cryo_brain_decoder"

# A measured-score function: workdir -> score dict (Grok G10 shape).
ScoreFn = Callable[[Path], dict[str, Any]]


def _step_enum(current: int, allowed: tuple[int, ...]) -> int:
    if current in allowed:
        idx = allowed.index(current)
        return allowed[min(len(allowed) - 1, idx + 1)]
    return allowed[0]


def apply_research_bias(design: DesignConfig, pack: ContextPack) -> DesignConfig:
    """Nudge the proposed design using literature themes (§2.5 adoption)."""
    if not pack.hits:
        return design
    text = " ".join(hit.get("snippet", "") for hit in pack.hits).lower()
    if "fpga" in text or "parallel" in text:
        return replace(design, parallelism=_step_enum(design.parallelism, (1, 2, 4)))
    if "pipeline" in text or "latency" in text:
        return replace(design, pipeline_depth=min(16, design.pipeline_depth + 2))
    if "layer" in text or "depth" in text:
        return replace(design, num_layers=min(4, max(2, design.num_layers)))
    return design


@dataclass(frozen=True)
class StepResult:
    """Outcome of one measured proposal step (all numbers MEASURED, no proxy)."""

    step: int
    design: DesignConfig
    rtl_path: Path
    rtl_hash: str
    reward: float
    candidate_ler: float
    suppression: float
    valid: bool
    layers_passed: list[str]
    score: dict[str, Any]
    recorded: bool

    def climb_row(self) -> dict[str, Any]:
        """Row for ``artifacts/measured_climb.json`` (measured fields only)."""
        row: dict[str, Any] = {
            "step": self.step,
            "candidate_ler": self.candidate_ler,
            "suppression": self.suppression,
            "rtl_hash": self.rtl_hash,
        }
        area = self.score.get("area_um2")
        latency = self.score.get("latency_cycles")
        if area is not None:
            row["area_um2"] = float(area)
        if latency is not None:
            row["latency_cycles"] = int(latency)
        return row


def build_workdir(design: DesignConfig, scenario: dict[str, Any], *, task_root: Path = TASK_ROOT) -> Path:
    """Stage a task workdir with this design's REAL generated RTL.

    Lays out exactly what ``score_measured`` reads: ``scenario.json``,
    ``design_config.json`` and ``rtl/cryo_brain_decoder.sv``. The RTL is the real
    ``.sv`` from Grok's ``generate_rtl`` for ``design`` (not the unchanged stock
    RTL the old proxy staged).
    """
    workdir = stage_workdir(task_root, scenario=scenario, design=design.to_dict())
    generate_rtl(design, workdir / "rtl")  # overwrites rtl/cryo_brain_decoder.sv
    return workdir


def measured_reward(
    design: DesignConfig,
    scenario: dict[str, Any],
    *,
    score_fn: ScoreFn = score_measured,
    shots: int = 1000,
    seed: int = 1729,
    task_root: Path = TASK_ROOT,
) -> tuple[float, dict[str, Any], Path]:
    """The measured reward boundary (C4/GRPO consumes this).

    Generates RTL for ``design``, scores it via the measured ``score_fn``
    (default ``score_measured`` — runs verify + measure + synth), and returns
    ``(reward, score, rtl_path)``. Reward is ``score["reward"]``; verification
    failure zeroes it inside ``score_measured`` (``rtl_valid`` gate). No formula.
    """
    workdir = build_workdir(design, scenario, task_root=task_root)
    rtl_path = workdir / "rtl" / "cryo_brain_decoder.sv"
    score = score_fn(workdir)
    return float(score["reward"]), score, rtl_path


def run_proposal_step(
    *,
    step: int,
    design: DesignConfig,
    scenario: dict[str, Any],
    store: MemoryStore | None = None,
    score_fn: ScoreFn = score_measured,
    backend: str = "verilator+stim+yosys",
    shots: int = 1000,
    seed: int = 1729,
    task_root: Path = TASK_ROOT,
    bus: EventBus | None = None,
) -> StepResult:
    """One measured step: research -> propose -> RTL -> measure -> verify -> score -> memory.

    Executor events are appended in SPEC-v6 pipeline order. The measured numbers
    still come from a single ``score_fn`` boundary (default ``score_measured``)
    so trainers can monkeypatch one function. Measurement and verification bus
    events replay that score's sub-fields without re-running Verilator.

    A memory record is written only when the variant is measured-valid. Invalid
    variants carry reward 0.0 and are NOT recorded.
    """
    bus = bus or EventBus()
    design_id = f"d{step:03d}"

    pack = research_step(bus, design_id)
    biased_design = apply_research_bias(design, pack)
    architect_propose_step(
        bus,
        design_id,
        biased_design,
        context_pack=pack,
        prompt_influenced=biased_design != design,
    )
    design = biased_design

    workdir = stage_workdir(task_root, scenario=scenario, design=design.to_dict())
    rtl_path = rtl_generate_step(bus, design_id, design, workdir / "rtl")

    # Single monkeypatchable measured boundary.
    score = score_step(
        bus,
        design_id,
        workdir,
        score_fn=score_fn,
        shots=shots,
        seed=seed,
        emit=False,
    )

    measurement = score.get("measurement")
    if measurement is None:
        measurement = {
            "candidate_ler": float(score.get("ler", 1.0)),
            "mwpm_ler": float(score.get("mwpm_ler", 0.0)),
            "suppression": float(score.get("suppression", 0.0)),
            "rtl_valid": bool(score.get("valid", False)),
            "benchmark_vectors": int(
                (score.get("measurement") or {}).get("benchmark_vectors", 0)
            ),
        }
    measure_step(
        bus,
        design_id,
        rtl_path,
        scenario,
        measurement=measurement,
        shots=shots,
        seed=seed,
    )
    verify_step(
        bus,
        design_id,
        rtl_path,
        budget=CryoBudget.from_dict(
            {
                "max_latency_cycles": int(scenario.get("max_latency_cycles", 64)),
                "max_area_mm2": float(scenario.get("max_area_mm2", 0.06)),
                "max_power_mw": float(scenario.get("max_power_mw", 8.0)),
            }
        ),
        layers_passed=list(score.get("layers_passed", [])),
    )
    score_step(bus, design_id, workdir, score=score, emit=True)

    reward = float(score["reward"])
    valid = bool(score.get("valid", False))
    candidate_ler = float(score.get("ler", 1.0))
    suppression = float(score.get("suppression", 0.0))
    layers_passed = list(score.get("layers_passed", []))

    recorded = False
    digest = ""
    if valid:
        digest = _record_measured(
            store=store,
            step=step,
            design=design,
            rtl_path=rtl_path,
            score=score,
            layers_passed=layers_passed,
            backend=backend,
            bus=bus,
            design_id=design_id,
            context_pack=pack,
        )
        recorded = True
    else:
        try:
            digest = rtl_hash(rtl_path)
        except (FileNotFoundError, OSError):
            digest = ""

    return StepResult(
        step=step,
        design=design,
        rtl_path=rtl_path,
        rtl_hash=digest,
        reward=reward,
        candidate_ler=candidate_ler,
        suppression=suppression,
        valid=valid,
        layers_passed=layers_passed,
        score=score,
        recorded=recorded,
    )


def _record_measured(
    *,
    store: MemoryStore | None,
    step: int,
    design: DesignConfig,
    rtl_path: Path,
    score: dict[str, Any],
    layers_passed: list[str],
    backend: str,
    bus: EventBus | None = None,
    design_id: str | None = None,
    context_pack: ContextPack | None = None,
) -> str:
    """Persist a measured, verified variant; return its rtl_hash.

    Pulls the measured ``measurement`` / ``synth`` sub-dicts straight out of the
    ``score_measured`` output (Grok measure + synth shapes) — never a proxy.
    """
    measurement = score.get("measurement") or {
        "candidate_ler": float(score["ler"]),
        "mwpm_ler": float(score.get("mwpm_ler", 0.0)),
        "suppression": float(score.get("suppression", 0.0)),
    }
    synth = score.get("synth") or {
        "area_um2": float(score.get("area_um2", 0.0)),
        "latency_cycles": int(score.get("latency_cycles", 0)),
        "power_mw_est": float(score.get("power_mw", 0.0)),
        "valid": True,
    }
    provenance_tags = context_pack.memory_tags() if context_pack is not None else []

    record = MemoryRecord.build(
        rtl_path=str(rtl_path),
        design=design,
        measurement=measurement,
        synth=synth,
        verification=Verification.from_layers(layers_passed or None, passed=True),
        provenance={"step": step, "backend": backend, "tags": provenance_tags},
    )
    target = store if store is not None else MemoryStore()
    if bus is not None and design_id is not None:
        tags = list(record.provenance.tags)
        return memory_step(bus, design_id, target, record, memory_tags=tags)
    return target.record_variant(record)
