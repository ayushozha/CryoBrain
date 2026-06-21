"""Modal dispatch for CryoBrain RL training (SPEC-v5 C4 / MP3 + legacy CP4).

Two training drivers live behind this launcher:

  * **GRPO on the MEASURED reward (SPEC-v5 C4 — the climb).**
    ``run_grpo_training`` rolls out groups of proposed ``DesignConfig``s, scores
    each through the measured boundary (``measured_reward`` -> Grok
    ``score_measured``: Stim->Verilator real LER + Yosys + L1/L4/L5, reward 0.0
    on verification failure), computes group-relative advantages, and applies a
    GRPO policy update — writing a checkpoint per step that references the
    group's measured memory rows (``rtl_hash``). NO proxy/formula reward.

  * **Legacy CP4 graded hill-climb (pre-SPEC-v5).** ``run_training`` keeps
    dispatching the hidden-grader local trainer for backward-compatible
    importers (``cryobrain.rl.__init__``, ``scripts/run_rl.py``). New work
    targets GRPO.

Modal is the GPU + parallel-measurement sponsor. The Modal image installs the
REAL measure stack (verilator + yosys + stim/pymatching) so per-variant
measurement runs on the worker — not a pretend GPU. Modal is import- AND
token-guarded: this module imports cleanly on Windows with no Modal creds, and
falls back to the local CPU-numpy GRPO loop when Modal is unavailable.

Commands:

    # GRPO measured climb (local CPU numpy fallback when no Modal token):
    uv run python -m cryobrain.rl.modal_train --grpo --steps 20 --group-size 6

    # Real Modal GRPO run (Linux worker w/ verilator+yosys; needs MODAL_TOKEN_*):
    modal run cryobrain/rl/modal_train.py --steps 20

    # Legacy CP4 graded loop:
    uv run python -m cryobrain.rl.modal_train --steps 50
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from cryobrain.grader.score import score_measured
from cryobrain.rl.config import TrainConfig
from cryobrain.rl.grpo import CHECKPOINT_DIR, DesignPolicy, GRPOStepResult, grpo_step
from cryobrain.rl.local_trainer import run_local_training
from cryobrain.rl.proposal_loop import ROOT, TASK_ROOT, ScoreFn
from cryobrain.rl.rollout import default_policy_sampler, generate_rollout_group
from cryobrain.memory.store import MemoryStore

APP_NAME = "cryobrain-rl-co-design"
DEFAULT_GRPO_CLIMB = ROOT / "artifacts" / "measured_climb.json"


# =============================================================================
# GRPO measured training driver (backend-agnostic: local numpy or Modal worker)
# =============================================================================


def _load_scenario(task_root: Path = TASK_ROOT) -> dict[str, Any]:
    """Load the task scenario; mirror score_measured's grading floor knobs."""
    raw = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    raw.setdefault("benchmark_vectors", 64)
    return raw


def run_grpo_training(
    *,
    steps: int,
    group_size: int = 6,
    seed: int = 0,
    lr: float = 0.1,
    score_fn: ScoreFn = score_measured,
    store: MemoryStore | None = None,
    task_root: Path = TASK_ROOT,
    checkpoint_dir: Path = CHECKPOINT_DIR,
    climb_path: Path | None = DEFAULT_GRPO_CLIMB,
    backend: str = "local-numpy",
) -> dict[str, Any]:
    """Run GRPO on the MEASURED reward — the real suppression climb (MP3).

    Each step: sample a group of designs from the policy -> measure each via
    ``score_fn`` (default ``score_measured``; C3 swaps a Modal-fanned scorer in
    here) -> group-relative advantages from MEASURED rewards -> policy update ->
    checkpoint referencing the group's measured ``rtl_hash`` rows.

    The climb artifact records, per step, the MEASURED suppression of the group's
    best rollout (``history[].{step, candidate_ler, suppression, rtl_hash}``) so
    it validates against the measured-climb schema exactly like C5's.
    """
    scenario = _load_scenario(task_root)
    rng = np.random.default_rng(seed)
    policy = DesignPolicy(lr=lr)
    store = store if store is not None else MemoryStore()
    sampler = default_policy_sampler(policy)

    history: list[dict[str, Any]] = []
    steps_log: list[dict[str, Any]] = []
    for step in range(steps):
        group = generate_rollout_group(
            step=step,
            scenario=scenario,
            group_size=group_size,
            policy_sample=sampler,
            store=store,
            score_fn=score_fn,
            rng=rng,
            task_root=task_root,
        )
        result: GRPOStepResult = grpo_step(
            step=step,
            policy=policy,
            group=group,
            checkpoint_dir=checkpoint_dir,
            backend=backend,
        )

        # Climb row = the group's best MEASURED rollout (lowest LER among valid;
        # falls back to the best-reward rollout). Only emit on a valid variant so
        # the artifact stays measured-only.
        best = _best_valid(group)
        if best is not None:
            history.append(
                {
                    "step": step,
                    "candidate_ler": float(best.candidate_ler),
                    "suppression": float(best.suppression),
                    "rtl_hash": best.rtl_hash,
                }
            )

        steps_log.append(
            {
                "step": step,
                "mean_reward": result.mean_reward,
                "best_reward": result.best_reward,
                "best_suppression": result.best_suppression,
                "n_valid": result.n_valid,
                "advantages": result.advantages,
                "grad_norms": result.grad_norms,
                "checkpoint": result.checkpoint_path,
            }
        )

    payload: dict[str, Any] = {
        "backend": backend,
        "reward_source": "measured",
        "algorithm": "grpo",
        "steps": steps,
        "group_size": group_size,
        "memory_records": len(store),
        "final_policy": policy.state_dict(),
        "greedy_design": policy.argmax_design().to_dict(),
        "history": history,
        "steps_log": steps_log,
    }
    if climb_path is not None:
        _write_json(
            Path(climb_path),
            {k: payload[k] for k in ("backend", "reward_source", "steps", "history")},
        )
    return payload


def _best_valid(group: Any) -> Any:
    """The best valid rollout in a group (lowest measured LER), or None."""
    valid = [r for r in group.results if r.valid]
    if not valid:
        return None
    return min(valid, key=lambda r: r.candidate_ler)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# =============================================================================
# Modal app (real measure image; import- and token-guarded)
# =============================================================================


def _build_modal_app():
    """Construct the Modal app with the REAL measure image, or raise ImportError.

    The image installs verilator + yosys (the measure/synth stack) and the Stim
    physics deps so per-variant MEASUREMENT runs on the worker — the GRPO reward
    stays measured on Modal, exactly as on a local Linux box.
    """
    import modal

    root = Path(__file__).resolve().parents[2]
    image = (
        modal.Image.debian_slim(python_version="3.12")
        .apt_install("verilator", "yosys")
        .pip_install(
            "stim>=1.14",
            "pymatching>=2.0",
            "numpy>=1.26",
            "pydantic>=2.0",
            "matplotlib>=3.8",
            "exa-py>=1.0",
            "openai>=1.0",
            "python-dotenv>=1.0",
        )
        .add_local_dir(root / "cryobrain", remote_path="/root/cryobrain")
        .add_local_dir(root / "tasks" / "cryo_brain_decoder", remote_path="/root/tasks/cryo_brain_decoder")
    )

    app = modal.App(APP_NAME)

    @app.function(
        image=image,
        gpu="T4",
        timeout=60 * 60,
        secrets=[modal.Secret.from_name("cryobrain-modal", required=False)],
    )
    def grpo_remote(payload: dict[str, object]) -> dict[str, object]:
        """Run the GRPO measured climb on a Modal worker (real measure stack)."""
        from cryobrain.rl.modal_train import run_grpo_training as _run

        result = _run(
            steps=int(payload.get("steps", 20)),
            group_size=int(payload.get("group_size", 6)),
            seed=int(payload.get("seed", 0)),
            lr=float(payload.get("lr", 0.1)),
            backend="modal",
            climb_path=None,  # caller persists; worker returns the payload
        )
        result["backend"] = "modal"
        return result

    @app.function(
        image=image,
        gpu="T4",
        timeout=60 * 60,
        secrets=[modal.Secret.from_name("cryobrain-modal", required=False)],
    )
    def train_remote(config_dict: dict[str, object]) -> dict[str, object]:
        """Legacy CP4 graded loop on a Modal worker (back-compat)."""
        from cryobrain.rl.config import TrainConfig as TC
        from cryobrain.rl.local_trainer import run_local_training as run_train

        config = TC.from_dict(config_dict)
        result = run_train(config)
        result["backend"] = "modal"
        return result

    return app, grpo_remote, train_remote


def run_grpo(
    *,
    steps: int,
    group_size: int = 6,
    seed: int = 0,
    lr: float = 0.1,
    force_local: bool = False,
) -> dict[str, Any]:
    """Dispatch GRPO to Modal when configured, else run the local numpy climb.

    Token/import-guarded: with Modal installed AND ``MODAL_TOKEN_ID/SECRET`` set,
    the climb runs on a worker with the real measure stack; otherwise it runs the
    measured loop locally (note: real measurement needs Linux EDA — on Windows
    the local fallback produces invalid/zero-reward rollouts, which GRPO handles
    as zero-advantage steps).
    """
    if force_local or os.environ.get("CRYOBRAIN_FORCE_LOCAL", "").lower() in {"1", "true", "yes"}:
        return run_grpo_training(steps=steps, group_size=group_size, seed=seed, lr=lr)

    try:
        import modal  # noqa: F401
    except ImportError:
        return run_grpo_training(steps=steps, group_size=group_size, seed=seed, lr=lr)

    token_id = os.environ.get("MODAL_TOKEN_ID")
    token_secret = os.environ.get("MODAL_TOKEN_SECRET")
    if not (token_id and token_secret):
        result = run_grpo_training(steps=steps, group_size=group_size, seed=seed, lr=lr)
        result["note"] = "Modal present but MODAL_TOKEN_ID/SECRET unset; ran local measured GRPO"
        return result

    try:
        _, grpo_remote, _ = _build_modal_app()
        payload = grpo_remote.remote(
            {"steps": steps, "group_size": group_size, "seed": seed, "lr": lr}
        )
        if DEFAULT_GRPO_CLIMB:
            _write_json(
                DEFAULT_GRPO_CLIMB,
                {k: payload[k] for k in ("backend", "reward_source", "steps", "history")},
            )
        return payload
    except Exception as exc:  # pragma: no cover - network/credential failures
        result = run_grpo_training(steps=steps, group_size=group_size, seed=seed, lr=lr)
        result["note"] = f"Modal GRPO dispatch failed ({exc}); ran local measured GRPO"
        return result


# =============================================================================
# Legacy CP4 dispatch (kept for back-compat importers)
# =============================================================================


def run_training(config: TrainConfig, *, force_local: bool = False) -> dict[str, object]:
    """LEGACY: dispatch the CP4 hidden-grader loop to Modal or run it locally."""
    if force_local or os.environ.get("CRYOBRAIN_FORCE_LOCAL", "").lower() in {"1", "true", "yes"}:
        return run_local_training(config)

    try:
        import modal  # noqa: F401
    except ImportError:
        return run_local_training(config)

    token_id = os.environ.get("MODAL_TOKEN_ID")
    token_secret = os.environ.get("MODAL_TOKEN_SECRET")
    if not (token_id and token_secret):
        result = run_local_training(config)
        result["note"] = "Modal package present but MODAL_TOKEN_ID/SECRET unset; used real local graded training"
        return result

    try:
        _, _, train_remote = _build_modal_app()
        return train_remote.remote(config.to_dict())
    except Exception as exc:  # pragma: no cover - network/credential failures
        result = run_local_training(config)
        result["note"] = f"Modal dispatch failed ({exc}); used real local graded training"
        return result


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="CryoBrain RL training launcher (GRPO measured / legacy CP4)")
    parser.add_argument("--grpo", action="store_true", help="run GRPO on the MEASURED reward (SPEC-v5 C4)")
    parser.add_argument("--steps", type=int, default=50, help="Total optimization / GRPO steps")
    parser.add_argument("--group-size", type=int, default=6, help="GRPO rollouts per step")
    parser.add_argument("--lr", type=float, default=0.1, help="GRPO policy learning rate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts/climb_chart.json"))
    parser.add_argument("--designs-output", type=Path, default=Path("artifacts/designs.json"))
    parser.add_argument("--config", type=Path, help="Optional JSON TrainConfig override (legacy CP4)")
    parser.add_argument("--local", action="store_true", help="Force local instead of Modal")
    args = parser.parse_args()

    if args.grpo:
        result = run_grpo(
            steps=args.steps,
            group_size=args.group_size,
            seed=args.seed,
            lr=args.lr,
            force_local=args.local,
        )
        accepted = len(result.get("history", []))
        print(
            f"GRPO measured climb: {accepted}/{args.steps} steps with a valid measured variant, "
            f"{result.get('memory_records', 0)} memory records, backend={result.get('backend')}"
        )
        if not accepted:
            print(
                "No valid measured rollouts. On Windows (no Verilator/Yosys) this is expected; "
                "run on a Modal worker / WSL with the EDA stack for the real climb."
            )
        return

    # Legacy CP4 path
    if args.config and args.config.is_file():
        raw = json.loads(args.config.read_text(encoding="utf-8"))
        config = TrainConfig.from_dict(raw)
    else:
        config = TrainConfig(
            steps=args.steps,
            seed=args.seed,
            output=str(args.output),
            designs_output=str(args.designs_output),
        )

    result = run_training(config, force_local=args.local)
    print(json.dumps(result, indent=2))


def _register_modal_entrypoint():
    """Register `modal run` entrypoint when Modal is installed."""
    try:
        app, grpo_remote, train_remote = _build_modal_app()
    except Exception:
        return None

    @app.local_entrypoint()
    def modal_main(steps: int = 20, group_size: int = 6, seed: int = 0, lr: float = 0.1) -> None:
        """`modal run` default: the GRPO measured climb on a worker."""
        payload = grpo_remote.remote(
            {"steps": steps, "group_size": group_size, "seed": seed, "lr": lr}
        )
        out = DEFAULT_GRPO_CLIMB
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({k: payload[k] for k in ("backend", "reward_source", "steps", "history")}, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(payload, indent=2))

    return app


app = _register_modal_entrypoint()


if __name__ == "__main__":
    main()
