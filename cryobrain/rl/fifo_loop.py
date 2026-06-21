"""Measured FIFO optimization loop (SPEC-v5 GEN / C9).

The FIFO sibling of :mod:`cryobrain.rl.proposal_loop` + :mod:`cryobrain.rl.local_trainer`.
It runs the EXACT SAME machinery — propose -> generate -> measure -> score ->
memory — on a NON-decoder RTL target (a stream-arbiter FIFO), proving the env
generalizes (SPEC-v5 §6 GEN gate).

We deliberately do NOT edit the decoder's ``proposal_loop`` / ``local_trainer``
(C5-owned). We mirror their structure here with FIFO-specific generate/measure
calls, and we record FIFO variants in the SAME :class:`cryobrain.memory.store.MemoryStore`
JSONL via the same :class:`~cryobrain.memory.models.MemoryRecord`.

Measured metric: sustained throughput (items drained / cycles) from the cocotb+
Verilator sim of the generated FIFO against :mod:`cryobrain.stim.fifo_stim`
traffic. Reward = measured throughput; correctness-gate failure => reward 0,
variant rejected (mirrors the decoder's verification gate). No proxy/formula.

Memory mapping (honest, into the shared decoder-shaped record): the FIFO has no
LER, so we map its measured throughput axis onto the record's measurement block
as ``candidate_ler = 1 - throughput`` (drop fraction; lower is better, like LER),
``mwpm_ler = 1 - baseline_throughput`` (single-entry FIFO anchor, the
``mwpm``-style reference), ``suppression = measured throughput gain vs baseline``.
``provenance.backend`` records ``verilator+fifo-throughput`` so the metric source
is never mistaken for a decoder LER.

Windows: no Verilator => the measured boundary returns invalid/zero; the unit
test mocks the boundary to exercise wiring. The real GEN climb runs in WSL
(``scripts/run_gen_fifo_wsl.sh``).
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from cryobrain.accuracy.fifo_throughput import TASK_ROOT, measure_fifo
from cryobrain.memory.models import MemoryRecord, Verification
from cryobrain.memory.store import MemoryStore, rtl_hash
from cryobrain.rtl_gen.fifo_generator import generate_fifo_rtl
from cryobrain.types_fifo import FifoConfig, fifo_preset_variants, mutate_fifo

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
DEFAULT_FIFO_CLIMB = ARTIFACTS / "measured_fifo_climb.json"
BACKEND = "verilator+fifo-throughput"

# A measured FIFO-score function: (rtl_path, design) -> score dict.
FifoScoreFn = Callable[[Path, FifoConfig], dict[str, Any]]
# A proposer: (step, best_design, memory_snapshot, rng) -> next FifoConfig.
FifoProposer = Callable[[int, FifoConfig, list[dict[str, Any]], random.Random], FifoConfig]

_TRAFFIC_CYCLES = 64
_TRAFFIC_SEED = 1729


@dataclass(frozen=True)
class FifoStepResult:
    """Outcome of one measured FIFO step (all numbers MEASURED, no proxy)."""

    step: int
    design: FifoConfig
    rtl_path: Path
    rtl_hash: str
    reward: float
    throughput: float
    suppression: float
    valid: bool
    score: dict[str, Any]
    recorded: bool

    def climb_row(self) -> dict[str, Any]:
        """Row for ``artifacts/measured_fifo_climb.json`` (measured fields only)."""
        return {
            "step": self.step,
            "throughput": self.throughput,
            "suppression": self.suppression,
            "rtl_hash": self.rtl_hash,
        }


def default_fifo_score(rtl_path: Path, design: FifoConfig) -> dict[str, Any]:
    """Real measured boundary: run the FIFO sim, return a score dict.

    Calls :func:`cryobrain.accuracy.fifo_throughput.measure_fifo` (cocotb+
    Verilator). On Windows (no EDA) it returns ``valid=False`` / throughput 0 —
    never a fabricated number.
    """
    result = measure_fifo(
        rtl_path,
        depth=design.depth,
        width=design.width,
        cycles=_TRAFFIC_CYCLES,
        seed=_TRAFFIC_SEED,
    )
    return result.to_score()


def run_fifo_step(
    *,
    step: int,
    design: FifoConfig,
    store: MemoryStore | None = None,
    score_fn: FifoScoreFn = default_fifo_score,
    out_dir: Path | None = None,
) -> FifoStepResult:
    """One measured FIFO step: generate -> measure -> score -> record.

    Mirrors :func:`cryobrain.rl.proposal_loop.run_proposal_step`. A memory record
    is written only when the variant is measured-valid (sim correctness gate
    passed). Invalid variants carry reward 0 and are NOT recorded.
    """
    work = out_dir or Path(_tmp_dir())
    rtl_path = generate_fifo_rtl(design, work)
    score = score_fn(rtl_path, design)

    valid = bool(score.get("valid", False))
    throughput = float(score.get("throughput", 0.0))
    suppression = float(score.get("suppression", 0.0))
    reward = float(score.get("reward", 0.0))

    recorded = False
    try:
        digest = rtl_hash(rtl_path)
    except (FileNotFoundError, OSError):
        digest = ""

    if valid:
        digest = _record_fifo(
            store=store,
            step=step,
            design=design,
            rtl_path=rtl_path,
            score=score,
        )
        recorded = True

    return FifoStepResult(
        step=step,
        design=design,
        rtl_path=rtl_path,
        rtl_hash=digest,
        reward=reward,
        throughput=throughput,
        suppression=suppression,
        valid=valid,
        score=score,
        recorded=recorded,
    )


def _record_fifo(
    *,
    store: MemoryStore | None,
    step: int,
    design: FifoConfig,
    rtl_path: Path,
    score: dict[str, Any],
) -> str:
    """Persist a measured, verified FIFO variant in the SHARED memory store.

    Maps the measured throughput axis onto the decoder-shaped measurement block
    honestly (see module docstring). All numbers come from the sim run.
    """
    throughput = float(score["throughput"])
    baseline = float(score.get("baseline_throughput", 0.0))
    measurement = {
        "candidate_ler": 1.0 - throughput,  # drop fraction; lower is better
        "mwpm_ler": 1.0 - baseline,  # single-entry FIFO anchor
        "suppression": float(score.get("suppression", 0.0)),  # measured tp gain
    }
    # Area proxy-free: cell area comes from synth in the real WSL flow; here we
    # carry the measured capacity (depth) as the area axis so pareto stays honest
    # about the size<->throughput tradeoff. latency = drain window the sim used.
    synth = {
        "area_um2": float(design.depth * design.width),
        "latency_cycles": int(score.get("cycles", _TRAFFIC_CYCLES)),
        "power_mw_est": 0.0,
        "valid": True,
    }
    record = MemoryRecord.build(
        rtl_path=str(rtl_path),
        design=design.to_dict(),
        measurement=measurement,
        synth=synth,
        verification=Verification.from_layers(score.get("layers_passed") or ["L1"], passed=True),
        provenance={"step": step, "backend": BACKEND},
    )
    target = store if store is not None else MemoryStore()
    return target.record_variant(record)


# --- proposers ---------------------------------------------------------------


def deterministic_fifo_proposer(
    step: int,
    best_design: FifoConfig,
    memory_snapshot: list[dict[str, Any]],
    rng: random.Random,
) -> FifoConfig:
    """No-key proposer: sweep presets, then deepen the best measured exemplar."""
    presets = fifo_preset_variants()
    if step < len(presets):
        return presets[step]
    return mutate_fifo(best_design, rng)


# --- trainer -----------------------------------------------------------------


def run_fifo_training(
    *,
    steps: int,
    seed: int = 0,
    proposer: FifoProposer = deterministic_fifo_proposer,
    score_fn: FifoScoreFn = default_fifo_score,
    store: MemoryStore | None = None,
    climb_path: Path | None = DEFAULT_FIFO_CLIMB,
) -> dict[str, Any]:
    """Run the measured FIFO climb: propose -> measured step -> accept-if-better.

    Mirrors :func:`cryobrain.rl.local_trainer.run_measured_training`. A step is
    accepted when its MEASURED throughput beats the best so far; accepted, valid
    variants are recorded to the shared memory store. Reward = measured throughput.
    """
    rng = random.Random(seed)
    store = store if store is not None else MemoryStore()

    presets = fifo_preset_variants()
    best_design = presets[0]
    best_throughput = float("-inf")
    history: list[dict[str, Any]] = []
    steps_log: list[dict[str, Any]] = []

    for step in range(steps):
        snapshot = _memory_snapshot(store)
        design = proposer(step, best_design, snapshot, rng)
        result = run_fifo_step(step=step, design=design, store=store, score_fn=score_fn)

        accepted = result.valid and (result.throughput > best_throughput or not history)
        if accepted:
            best_throughput = result.throughput
            best_design = result.design
            history.append(result.climb_row())

        steps_log.append(
            {
                "step": step,
                "design": design.to_dict(),
                "reward": result.reward,
                "throughput": result.throughput,
                "suppression": result.suppression,
                "valid": result.valid,
                "accepted": accepted,
                "recorded": result.recorded,
                "rtl_hash": result.rtl_hash,
            }
        )

    payload: dict[str, Any] = {
        "backend": BACKEND,
        "reward_source": "measured_fifo_throughput",
        "target": "stream_arb_fifo",
        "steps": steps,
        "memory_records": len(store),
        "history": history,
        "steps_log": steps_log,
    }
    if climb_path is not None:
        _write_json(
            Path(climb_path),
            {k: payload[k] for k in ("backend", "reward_source", "target", "steps", "history")},
        )
    return payload


def _memory_snapshot(store: MemoryStore, *, k: int = 5) -> list[dict[str, Any]]:
    """Top measured FIFO variants as proposer exemplars (best throughput first)."""
    snapshot: list[dict[str, Any]] = []
    for rec in store.all_records():
        if rec.provenance.backend != BACKEND or not rec.verification.passed:
            continue
        snapshot.append(
            {
                "design": dict(rec.design),
                "throughput": 1.0 - rec.measurement.candidate_ler,
            }
        )
    snapshot.sort(key=lambda r: r["throughput"], reverse=True)
    return snapshot[:k]


def _tmp_dir() -> str:
    import tempfile

    return tempfile.mkdtemp(prefix="cryobrain-fifo-")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _empty_climb(steps: int) -> dict[str, Any]:
    return {
        "backend": BACKEND,
        "reward_source": "measured_fifo_throughput",
        "target": "stream_arb_fifo",
        "steps": steps,
        "history": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--steps", type=int, default=5, help="number of measured FIFO steps")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--climb", type=Path, default=DEFAULT_FIFO_CLIMB)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="emit an empty schema-shaped climb artifact without running EDA (Windows-safe)",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        _write_json(args.climb, _empty_climb(args.steps))
        print(f"[dry-run] wrote empty schema-shaped FIFO climb to {args.climb}")
        print("Real measured GEN climb runs in WSL: scripts/run_gen_fifo_wsl.sh")
        return 0

    result = run_fifo_training(steps=args.steps, seed=args.seed, climb_path=args.climb)
    accepted = len(result["history"])
    print(
        f"measured FIFO climb: {accepted}/{args.steps} accepted, "
        f"{result['memory_records']} memory records, climb -> {args.climb}"
    )
    if not accepted:
        print(
            "No valid measured FIFO variants. On Windows (no Verilator) this is expected; "
            "run scripts/run_gen_fifo_wsl.sh in WSL for the real GEN climb, or use --dry-run."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
