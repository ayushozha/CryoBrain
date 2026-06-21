"""Measured local trainer (SPEC-v5 C5 / MP3) — kills the proxy knob-sweep.

Each step is the measured loop (driven through :mod:`cryobrain.rl.proposal_loop`):

    propose DesignConfig -> generate_rtl -> verify (L1/L4/L5) -> measure_candidate_ler
        -> score_measured -> record_variant

A step is *accepted* when its MEASURED suppression improves on the best so far.
The reward moves only on measured change (Grok ``score_measured``); there is NO
``estimate_hardware_metrics`` / ``decoder_quality_multiplier`` / ``simulate_candidate_ler``
formula anywhere in this path — the old proxy trainer is gone.

Proposer:
  * default (``--no-fireworks``, the Windows-safe path): a deterministic proposer
    that seeds from preset variants and mutates the best measured exemplar in
    memory. Runs with no API key.
  * ``--fireworks`` (key required): Grok C2's ``propose_next_design`` over a
    measured-memory snapshot.

Artifacts (MEASURED runs only):
  * ``artifacts/measured_climb.json`` — ``history[].{step, candidate_ler, suppression, rtl_hash}``
  * ``artifacts/measured_memory_ab.json`` — ``with_memory[]`` / ``without_memory[]``
    series, each a measured climb (memory-on proposer vs memory-off sweep).

The full end-to-end climb (real Verilator/Yosys) runs in WSL via
``scripts/run_c5_climb_wsl.sh``. On Windows without EDA, ``score_measured``
returns invalid/zero-reward variants — use ``--dry-run`` to emit an empty but
schema-shaped climb artifact, or run the WSL script for the real MP3 climb.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Callable

from cryobrain.design.config import mutate, preset_variants
from cryobrain.grader.score import score_measured
from cryobrain.memory.store import MemoryStore
from cryobrain.rl.proposal_loop import (
    ROOT,
    TASK_ROOT,
    ScoreFn,
    StepResult,
    run_proposal_step,
)
from cryobrain.types import DesignConfig

ARTIFACTS = ROOT / "artifacts"
DEFAULT_CLIMB = ARTIFACTS / "measured_climb.json"
DEFAULT_MEMORY_AB = ARTIFACTS / "measured_memory_ab.json"

# A proposer: (step, best_design, memory_snapshot, rng) -> next DesignConfig.
Proposer = Callable[[int, DesignConfig, list[dict[str, Any]], random.Random], DesignConfig]


def _load_scenario(task_root: Path = TASK_ROOT) -> dict[str, Any]:
    raw = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    # Grading floor mirrors score_measured; keep shots/vectors sane for measurement.
    raw.setdefault("benchmark_vectors", 64)
    return raw


# --- proposers ----------------------------------------------------------------


def deterministic_proposer(
    step: int,
    best_design: DesignConfig,
    memory_snapshot: list[dict[str, Any]],
    rng: random.Random,
) -> DesignConfig:
    """No-key proposer: seed from presets, then mutate the best measured exemplar.

    First few steps sweep the distinct presets (cold start / exploration); after
    that, mutate the current best design (the highest-measured-suppression
    variant carried in by the trainer). Deterministic given ``rng``.
    """
    presets = preset_variants()
    if step < len(presets):
        return presets[step]
    return mutate(best_design, rng)


def fireworks_proposer(
    step: int,
    best_design: DesignConfig,
    memory_snapshot: list[dict[str, Any]],
    rng: random.Random,
) -> DesignConfig:
    """Live Fireworks proposer (C2). Raises without ``FIREWORKS_API_KEY``."""
    from cryobrain.rl.proposer import propose_next_design

    design = propose_next_design({"best": memory_snapshot})
    return design if design is not None else mutate(best_design, rng)


# --- trainer ------------------------------------------------------------------


def run_measured_training(
    *,
    steps: int,
    seed: int = 0,
    proposer: Proposer = deterministic_proposer,
    use_memory: bool = True,
    score_fn: ScoreFn = score_measured,
    store: MemoryStore | None = None,
    task_root: Path = TASK_ROOT,
    climb_path: Path | None = DEFAULT_CLIMB,
    backend: str = "verilator+stim+yosys",
) -> dict[str, Any]:
    """Run the measured climb: propose -> measured step -> accept-if-better.

    A step is accepted when its MEASURED suppression beats the best accepted so
    far. Accepted steps append a row (with ``rtl_hash`` + measured ``candidate_ler``)
    to the climb history; every accepted, valid variant is recorded to memory by
    ``run_proposal_step``. Reward derives from ``score_measured`` only.
    """
    scenario = _load_scenario(task_root)
    rng = random.Random(seed)
    store = store if store is not None else MemoryStore()

    presets = preset_variants()
    best_design = presets[0]
    best_suppression = float("-inf")
    history: list[dict[str, Any]] = []
    steps_log: list[dict[str, Any]] = []

    for step in range(steps):
        snapshot = _memory_snapshot(store) if use_memory else []
        design = proposer(step, best_design, snapshot, rng)
        result = run_proposal_step(
            step=step,
            design=design,
            scenario=scenario,
            store=store,
            score_fn=score_fn,
            backend=backend,
            task_root=task_root,
        )

        # Accept only on MEASURED improvement; first valid variant sets the bar.
        accepted = result.valid and (result.suppression > best_suppression or not history)
        if accepted:
            best_suppression = result.suppression
            best_design = result.design
            history.append(result.climb_row())

        steps_log.append(
            {
                "step": step,
                "design": design.to_dict(),
                "reward": result.reward,
                "candidate_ler": result.candidate_ler,
                "suppression": result.suppression,
                "valid": result.valid,
                "accepted": accepted,
                "recorded": result.recorded,
                "layers_passed": result.layers_passed,
                "rtl_hash": result.rtl_hash,
            }
        )

    payload: dict[str, Any] = {
        "backend": backend,
        "reward_source": "score_measured",
        "use_memory": use_memory,
        "steps": steps,
        "memory_records": len(store),
        "history": history,
        "steps_log": steps_log,
    }
    if climb_path is not None:
        _write_json(Path(climb_path), {k: payload[k] for k in ("backend", "reward_source", "steps", "history")})
    return payload


def _memory_snapshot(store: MemoryStore, *, k: int = 5) -> list[dict[str, Any]]:
    """Top measured variants as proposer exemplars (lowest measured LER first)."""
    candidates = store.query_pareto_candidates()[:k]
    return [
        {
            "design": _design_for_hash(store, c["rtl_hash"]),
            "measurement": {"candidate_ler": c["ler"]},
            "metrics": {"area_um2": c["area_um2"], "latency_cycles": c["latency_cycles"]},
        }
        for c in candidates
    ]


def _design_for_hash(store: MemoryStore, digest: str) -> dict[str, Any]:
    """Design dict for a record by its rtl_hash (store is keyed by rtl_hash)."""
    rec = store._records.get(digest)  # noqa: SLF001 — intra-package read of own store
    return dict(rec.design) if rec is not None else {}


def run_memory_ab(
    *,
    steps: int,
    seed: int = 0,
    score_fn: ScoreFn = score_measured,
    task_root: Path = TASK_ROOT,
    ab_path: Path | None = DEFAULT_MEMORY_AB,
) -> dict[str, Any]:
    """Two measured climbs: memory-on (mutate best) vs memory-off (preset sweep).

    Both series are produced by the SAME measured loop; the only difference is
    whether the proposer reads memory. Each row is a measured climb row.
    """
    with_memory = run_measured_training(
        steps=steps,
        seed=seed,
        proposer=deterministic_proposer,
        use_memory=True,
        score_fn=score_fn,
        store=MemoryStore(_tmp_store("ab_with")),
        task_root=task_root,
        climb_path=None,
    )

    def _sweep_only(step: int, best: DesignConfig, snap: list[dict[str, Any]], rng: random.Random) -> DesignConfig:
        presets = preset_variants()
        return presets[step % len(presets)]

    without_memory = run_measured_training(
        steps=steps,
        seed=seed,
        proposer=_sweep_only,
        use_memory=False,
        score_fn=score_fn,
        store=MemoryStore(_tmp_store("ab_without")),
        task_root=task_root,
        climb_path=None,
    )

    payload = {
        "reward_source": "score_measured",
        "with_memory": with_memory["history"],
        "without_memory": without_memory["history"],
    }
    if ab_path is not None:
        _write_json(Path(ab_path), payload)
    return payload


def _tmp_store(tag: str) -> Path:
    import tempfile

    return Path(tempfile.mkdtemp(prefix=f"cryobrain-{tag}-")) / "measured_variants.jsonl"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# --- CLI ----------------------------------------------------------------------


def _empty_climb(steps: int, backend: str) -> dict[str, Any]:
    return {"backend": backend, "reward_source": "score_measured", "steps": steps, "history": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steps", type=int, default=5, help="number of measured proposal steps")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--no-fireworks",
        dest="fireworks",
        action="store_false",
        help="use the deterministic proposer (default-safe, no API key)",
    )
    parser.add_argument(
        "--fireworks",
        dest="fireworks",
        action="store_true",
        help="use the live Fireworks proposer (requires FIREWORKS_API_KEY)",
    )
    parser.set_defaults(fireworks=False)
    parser.add_argument("--climb", type=Path, default=DEFAULT_CLIMB)
    parser.add_argument("--memory-ab", action="store_true", help="also emit measured_memory_ab.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="emit an empty schema-shaped climb artifact without running EDA (Windows-safe)",
    )
    args = parser.parse_args(argv)

    backend = "verilator+stim+yosys"
    if args.dry_run:
        _write_json(args.climb, _empty_climb(args.steps, backend))
        print(f"[dry-run] wrote empty schema-shaped climb to {args.climb}")
        print("Real measured climb runs in WSL: scripts/run_c5_climb_wsl.sh")
        return 0

    proposer = fireworks_proposer if args.fireworks else deterministic_proposer
    result = run_measured_training(
        steps=args.steps,
        seed=args.seed,
        proposer=proposer,
        climb_path=args.climb,
        backend=backend,
    )
    if args.memory_ab:
        run_memory_ab(steps=args.steps, seed=args.seed)

    accepted = len(result["history"])
    print(
        f"measured climb: {accepted}/{args.steps} accepted, "
        f"{result['memory_records']} memory records, climb -> {args.climb}"
    )
    if not accepted:
        print(
            "No valid measured variants. On Windows (no Verilator/Yosys) this is expected; "
            "run scripts/run_c5_climb_wsl.sh in WSL for the real MP3 climb, or use --dry-run."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# =============================================================================
# LEGACY CP4 graded hill-climb (pre-SPEC-v5) — kept ONLY for backward-compatible
# importers (cryobrain.rl.__init__, cryobrain.rl.modal_train, scripts/run_memory_ab,
# tests/test_cp4_training). It is NOT the SPEC-v5 measured loop and is NOT used by
# the measured path above. The SPEC-v5 reward is score_measured (see
# run_measured_training); this legacy block drives the hidden CP4 grade_fn and is
# retained so C3/C4-owned modal_train keeps importing. New work targets the
# measured loop, not these functions.
# =============================================================================

import importlib.util as _importlib_util  # noqa: E402
from dataclasses import asdict as _asdict  # noqa: E402
from typing import Callable as _Callable  # noqa: E402

from cryobrain.calibration.cp3 import stage_workdir as _stage_workdir  # noqa: E402
from cryobrain.cost_model.npu_cost import estimate_hardware_metrics as _estimate_hardware_metrics  # noqa: E402
from cryobrain.integrations.exa_rag import (  # noqa: E402
    search_decoder_literature as _search_decoder_literature,
    seed_memory_tags as _seed_memory_tags,
)
from cryobrain.integrations.fireworks import propose_design_config as _propose_design_config  # noqa: E402
from cryobrain.memory.buffer import VerifiedDesignBuffer as _VerifiedDesignBuffer  # noqa: E402
from cryobrain.memory.retrieve import retrieve as _retrieve  # noqa: E402
from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm as _ler_suppression_vs_mwpm  # noqa: E402
from cryobrain.rl.config import CurriculumStage as _CurriculumStage, TrainConfig as _TrainConfig  # noqa: E402

_LEGACY_TASK_ROOT = TASK_ROOT
_LegacyGradeFn = _Callable[[Path], dict[str, object]]


def _load_grade_fn(task_root: Path = _LEGACY_TASK_ROOT) -> _LegacyGradeFn:
    grade_path = task_root / "donotaccess" / "grade.py"
    spec = _importlib_util.spec_from_file_location("cryo_brain_decoder_grade", grade_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {grade_path}")
    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hidden_root = task_root / "donotaccess"

    def grade(workdir: Path) -> dict[str, object]:
        return module.grade(workdir, hidden_root=hidden_root)

    return grade


def _design_sweep(seed: int) -> list[DesignConfig]:
    base = [
        DesignConfig(bitwidth=4, num_layers=1, parallelism=1, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=2, num_layers=1, parallelism=1, pipeline_depth=4, window_length=4),
        DesignConfig(bitwidth=2, num_layers=1, parallelism=2, pipeline_depth=2, window_length=4),
        DesignConfig(bitwidth=4, num_layers=1, parallelism=2, pipeline_depth=2, window_length=8),
        DesignConfig(bitwidth=2, num_layers=2, parallelism=2, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=4, num_layers=2, parallelism=2, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=4, num_layers=2, parallelism=4, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=8, num_layers=1, parallelism=4, pipeline_depth=4, window_length=8),
    ]
    tail = base[1:]
    random.Random(seed).shuffle(tail)
    return [base[0], *tail]


def _scenario_for_stage(base_scenario, stage, *, seed, step):
    scenario = dict(base_scenario)
    scenario.update(
        {
            "distance": stage.distance,
            "noise_rate": stage.noise_rate,
            "max_latency_cycles": stage.budget.max_latency_cycles,
            "max_area_mm2": stage.budget.max_area_mm2,
            "max_power_mw": stage.budget.max_power_mw,
            "benchmark_seed": seed * 1009 + step,
            "benchmark_vectors": 64,
        }
    )
    return scenario


def _stage_index(step, steps, stages):
    if not stages:
        return 0
    return min(len(stages) - 1, step * len(stages) // max(steps, 1))


def _mutate_from_exemplar(exemplar, step, seed):
    raw = exemplar.get("design", {})
    base = DesignConfig.from_dict(raw if isinstance(raw, dict) else {})
    rng = random.Random(seed * 1009 + step)
    knobs = ("bitwidth", "num_layers", "parallelism", "pipeline_depth", "window_length")
    values = list(base.to_dict().values())
    idx = step % len(knobs)
    choices = {
        "bitwidth": [2, 4, 8],
        "num_layers": [1, 2, 4],
        "parallelism": [1, 2, 4],
        "pipeline_depth": [2, 4, 8, 16],
        "window_length": [4, 8, 12, 16],
    }
    key = knobs[idx]
    current = getattr(base, key)
    alt = [v for v in choices[key] if v != current]
    if alt:
        values[idx] = rng.choice(alt)
    return DesignConfig(**dict(zip(knobs, values, strict=True)))


def _pick_candidate(*, step, candidates, config, scenario, buffer):
    exemplars: list[dict[str, object]] = []
    if config.memory_enabled and buffer is not None:
        exemplars = _retrieve({"scenario": scenario}, buffer_path=config.memory_buffer, k=config.memory_top_k)
        if exemplars:
            return _mutate_from_exemplar(exemplars[0], step, config.seed), exemplars
    if config.use_fireworks and step % 5 == 4:
        proposed = _propose_design_config(scenario=scenario, exemplars=exemplars)
        if proposed is not None:
            return proposed, exemplars
    return candidates[step % len(candidates)], exemplars


def _metric(subscores, name, key, default=0.0):
    section = subscores.get(name, {})
    if not isinstance(section, dict):
        return default
    if key == "raw_score":
        return float(section.get("raw_score", default))
    result = section.get("result", {})
    return float(result.get(key, default)) if isinstance(result, dict) else default


def run_graded_training(config, *, grade_fn=None, task_root=_LEGACY_TASK_ROOT):
    """LEGACY CP4 hill-climb scored by the hidden grader (not the measured loop)."""
    task_root = Path(task_root)
    grade_fn = grade_fn or _load_grade_fn(task_root)
    base_scenario = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    candidates = _design_sweep(config.seed)
    stages = list(config.curriculum)
    buffer = _VerifiedDesignBuffer(config.memory_buffer) if config.memory_enabled else None
    exa_tags: list[str] = []
    if config.exa_seed:
        exa_tags = _seed_memory_tags(_search_decoder_literature())

    history: list[dict[str, object]] = []
    designs: list[dict[str, object]] = []
    transitions: list[dict[str, object]] = []
    accepted_reward = 0.0
    accepted_design = candidates[0]
    last_stage_idx = 0

    for step in range(config.steps):
        stage_idx = _stage_index(step, config.steps, stages)
        stage = stages[stage_idx]
        if step and stage_idx != last_stage_idx:
            transitions.append(
                {
                    "step": step,
                    "from_distance": stages[last_stage_idx].distance,
                    "to_distance": stage.distance,
                    "reward_at_transition": round(accepted_reward, 4),
                }
            )
            last_stage_idx = stage_idx

        scenario = _scenario_for_stage(base_scenario, stage, seed=config.seed, step=step)
        candidate, exemplars = _pick_candidate(
            step=step, candidates=candidates, config=config, scenario=scenario, buffer=buffer
        )
        workdir = _stage_workdir(task_root, scenario=scenario, design=candidate.to_dict())
        result = grade_fn(workdir)
        candidate_reward = float(result["reward"])
        subscores = result.get("subscores", {})
        if not isinstance(subscores, dict):
            subscores = {}

        if step == 0 or candidate_reward >= accepted_reward:
            accepted_reward = candidate_reward
            accepted_design = candidate

        row = {
            "step": step,
            "reward": round(accepted_reward, 6),
            "candidate_reward": round(candidate_reward, 6),
            "distance": stage.distance,
            "stage": stage_idx,
            "noise_rate": stage.noise_rate,
            "accepted": candidate == accepted_design,
            "design": accepted_design.to_dict(),
            "candidate_design": candidate.to_dict(),
            "hard_caps": result.get("hard_caps", []),
            "ler_suppression": round(_metric(subscores, "ler_suppression", "raw_score"), 6),
            "latency_score": round(_metric(subscores, "latency", "raw_score"), 6),
            "area_score": round(_metric(subscores, "area", "raw_score"), 6),
            "benchmark_exactness": round(_metric(subscores, "rtl_validity", "benchmark_exactness"), 6),
            "memory_exemplars": len(exemplars),
        }
        history.append(row)

        if buffer is not None and candidate_reward > 0.0 and not result.get("hard_caps"):
            latency_section = subscores.get("latency", {})
            metrics = latency_section.get("result", {}) if isinstance(latency_section, dict) else {}
            if not isinstance(metrics, dict):
                metrics = _estimate_hardware_metrics(candidate).to_dict()
            buffer.add_from_grade(
                design=candidate.to_dict(),
                reward=candidate_reward,
                metrics=metrics,
                distance=stage.distance,
                noise_rate=stage.noise_rate,
                source="cp4_trainer",
                tags=exa_tags,
            )

        if candidate_reward > 0.0 and not result.get("hard_caps"):
            latency_section = subscores.get("latency", {})
            metrics = latency_section.get("result", {}) if isinstance(latency_section, dict) else {}
            if not isinstance(metrics, dict):
                metrics = _estimate_hardware_metrics(candidate).to_dict()
            designs.append(
                {
                    "name": f"agent-step-{step}",
                    "kind": "policy",
                    "step": step,
                    "distance": stage.distance,
                    "reward": round(candidate_reward, 6),
                    "area_mm2": float(metrics.get("area_mm2", 0.0)),
                    "latency_cycles": int(metrics.get("latency_cycles", 0)),
                    "power_mw": float(metrics.get("power_mw", 0.0)),
                    "ler_suppression": row["ler_suppression"],
                    "benchmark_exactness": row["benchmark_exactness"],
                    "design": candidate.to_dict(),
                    "source": "hidden_grader",
                }
            )

    output = Path(config.output)
    designs_path = Path(config.designs_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    designs_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "start_reward": history[0]["reward"] if history else 0.0,
        "end_reward": history[-1]["reward"] if history else 0.0,
        "max_reward": max((h["reward"] for h in history), default=0.0),
        "stages_completed": (max((int(h["stage"]) for h in history), default=0) + 1) if history else 0,
        "accepted_design": accepted_design.to_dict(),
    }
    payload: dict[str, object] = {
        "backend": "real_local",
        "memory_enabled": config.memory_enabled,
        "use_fireworks": config.use_fireworks,
        "exa_seed": config.exa_seed,
        "memory_records": len(buffer) if buffer is not None else 0,
        "reward_source": str(task_root / "donotaccess" / "grade.py"),
        "config": config.to_dict(),
        "steps": config.steps,
        "final_distance": stages[last_stage_idx].distance if stages else None,
        "history": history,
        "curriculum_transitions": transitions,
        "summary": summary,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    designs_path.write_text(json.dumps(designs, indent=2), encoding="utf-8")
    return payload


def run_local_training(config) -> dict[str, object]:
    """Backward-compatible CP4 entrypoint (legacy hidden-grader hill-climb)."""
    return run_graded_training(config)


def baseline_designs() -> list[dict[str, object]]:
    """LEGACY Pareto anchors for the CP4 designs.json (proxy metrics, not measured)."""
    starter = DesignConfig(bitwidth=4, num_layers=2, parallelism=1, pipeline_depth=4, window_length=8)
    starter_metrics = _estimate_hardware_metrics(starter)
    neural = DesignConfig(bitwidth=8, num_layers=4, parallelism=1, pipeline_depth=16, window_length=16)
    neural_metrics = _estimate_hardware_metrics(neural)
    mwpm_ler = 0.022
    return [
        {
            "name": "mwpm",
            "kind": "baseline",
            "area_mm2": 0.06,
            "latency_cycles": 12,
            "power_mw": 2.0,
            "ler_suppression": 0.0,
            "reward": 0.0,
        },
        {
            "name": "starter",
            "kind": "policy",
            "area_mm2": round(starter_metrics.area_mm2, 6),
            "latency_cycles": starter_metrics.latency_cycles,
            "power_mw": round(starter_metrics.power_mw, 4),
            "ler_suppression": round(_ler_suppression_vs_mwpm(0.017, mwpm_ler), 4),
            "reward": 0.32,
            "design": _asdict(starter),
        },
        {
            "name": "neural-ref",
            "kind": "baseline",
            "area_mm2": round(neural_metrics.area_mm2, 6),
            "latency_cycles": neural_metrics.latency_cycles,
            "power_mw": round(neural_metrics.power_mw, 4),
            "ler_suppression": round(_ler_suppression_vs_mwpm(0.008, mwpm_ler), 4),
            "reward": 0.0,
        },
    ]
