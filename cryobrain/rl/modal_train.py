"""Modal dispatch for the CP4 real graded training loop (SPEC F6, CP4).

Commands:

    uv run --extra rl python -m cryobrain.rl.modal_train --steps 50
    uv run python scripts/run_rl.py --steps 50
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cryobrain.rl.config import TrainConfig
from cryobrain.rl.local_trainer import run_local_training

APP_NAME = "cryobrain-rl-co-design"


def _build_modal_app():
    """Construct the optional Modal app, or raise ImportError if Modal is unavailable."""
    import modal

    root = Path(__file__).resolve().parents[2]
    image = (
        modal.Image.debian_slim(python_version="3.12")
        .apt_install("verilator", "yosys")
        .pip_install(
            "stim>=1.14",
            "pymatching>=2.0",
            "numpy>=1.26",
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
    def train_remote(config_dict: dict[str, object]) -> dict[str, object]:
        from cryobrain.rl.config import TrainConfig as TC
        from cryobrain.rl.local_trainer import run_local_training as run_train

        config = TC.from_dict(config_dict)
        result = run_train(config)
        result["backend"] = "modal"
        return result

    return app, train_remote


def run_training(config: TrainConfig, *, force_local: bool = False) -> dict[str, object]:
    """Dispatch to Modal when configured, otherwise run the real local grader loop."""
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
        _, train_remote = _build_modal_app()
        return train_remote.remote(config.to_dict())
    except Exception as exc:  # pragma: no cover - network/credential failures
        result = run_local_training(config)
        result["note"] = f"Modal dispatch failed ({exc}); used real local graded training"
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="CryoBrain RL training launcher (F6/F7)")
    parser.add_argument("--steps", type=int, default=50, help="Total optimization steps")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts/climb_chart.json"))
    parser.add_argument("--designs-output", type=Path, default=Path("artifacts/designs.json"))
    parser.add_argument("--config", type=Path, help="Optional JSON TrainConfig override")
    parser.add_argument("--local", action="store_true", help="Force real local training instead of Modal")
    args = parser.parse_args()

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
        app, train_remote = _build_modal_app()
    except Exception:
        return None

    @app.local_entrypoint()
    def modal_main(steps: int = 50, seed: int = 42) -> None:
        config = TrainConfig(steps=steps, seed=seed)
        payload = train_remote.remote(config.to_dict())
        out = Path(config.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))

    return app


app = _register_modal_entrypoint()


if __name__ == "__main__":
    main()
