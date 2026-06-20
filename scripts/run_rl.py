#!/usr/bin/env python3
"""CP4 helper - run real CryoBrain reward training locally, in WSL, or on Modal."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryobrain.rl.config import TrainConfig
from cryobrain.rl.modal_train import run_training


def _to_wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def _run_wsl_cp4(args: argparse.Namespace) -> int:
    script = _to_wsl_path(ROOT / "scripts" / "run_cp4_wsl.sh")
    cmd = [
        "wsl",
        "-e",
        "bash",
        script,
        "--steps",
        str(args.steps),
        "--seed",
        str(args.seed),
        "--output",
        _to_wsl_path(args.output.resolve()),
        "--designs-output",
        _to_wsl_path(args.designs_output.resolve()),
    ]
    if args.config:
        cmd.extend(["--config", _to_wsl_path(args.config.resolve())])
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="CP4: CryoBrain RL training launcher")
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts/climb_chart.json"))
    parser.add_argument("--designs-output", type=Path, default=Path("artifacts/designs.json"))
    parser.add_argument("--config", type=Path, help="Optional TrainConfig JSON")
    parser.add_argument("--local", action="store_true", help="Force real local training instead of Modal")
    args = parser.parse_args()

    from cryobrain.rtl_grader.flow import eda_tools_available

    if not eda_tools_available() and platform.system() == "Windows" and shutil.which("wsl"):
        print("EDA missing on Windows - running real CP4 training in WSL...")
        return _run_wsl_cp4(args)

    if args.config and args.config.is_file():
        config = TrainConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))
    else:
        config = TrainConfig(
            steps=args.steps,
            seed=args.seed,
            output=str(args.output),
            designs_output=str(args.designs_output),
        )

    result = run_training(config, force_local=args.local)
    print(json.dumps(result, indent=2))

    history = result.get("history", [])
    if isinstance(history, list) and len(history) >= 2:
        start = float(history[0].get("reward", 0.0))  # type: ignore[union-attr]
        end = float(history[-1].get("reward", 0.0))  # type: ignore[union-attr]
        if end <= start:
            print("WARNING: reward did not trend up - check CP3 calibration before long runs", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
