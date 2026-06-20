"""Modal RL co-design loop stub (SPEC F6, CP4).

Kick off with:
    uv run --extra rl python -m cryobrain.rl.modal_train --steps 50
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def run_local_stub(*, steps: int, output: Path) -> dict[str, object]:
    """Local fallback when Modal is unavailable — produces a climb-chart JSON."""
    history = []
    reward = 0.28
    for step in range(steps):
        reward = min(0.85, reward + 0.01 + (0.003 * (step % 5)))
        history.append({"step": step, "reward": round(reward, 4)})
    payload = {"backend": "local_stub", "steps": steps, "history": history}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="CryoBrain RL training launcher")
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("artifacts/climb_chart.json"))
    args = parser.parse_args()

    try:
        import modal  # noqa: F401
    except ImportError:
        result = run_local_stub(steps=args.steps, output=args.output)
        print(json.dumps(result, indent=2))
        return

    # Modal wiring lands here once credentials are configured.
    result = run_local_stub(steps=args.steps, output=args.output)
    print(json.dumps({"note": "modal package present; using local stub until app is deployed", **result}, indent=2))


if __name__ == "__main__":
    main()