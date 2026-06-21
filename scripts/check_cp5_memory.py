#!/usr/bin/env python3
"""SPEC2 CP5 gate: memory-on should match or beat memory-off climb."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    overlay_path = ROOT / "artifacts" / "memory_ab_overlay.json"
    if not overlay_path.is_file():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_memory_ab.py"), "--steps", "12"],
            check=True,
            cwd=ROOT,
        )
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    no_mem = overlay.get("without_memory", {})
    with_mem = overlay.get("with_memory", {})
    end_delta = float(with_mem.get("end_reward", 0.0)) - float(no_mem.get("end_reward", 0.0))
    slope_delta = float(with_mem.get("slope", 0.0)) - float(no_mem.get("slope", 0.0))
    ok = end_delta >= -0.005 or slope_delta > 0.0
    report = {
        "ok": ok,
        "cp5_memory": {
            "end_delta": round(end_delta, 6),
            "slope_delta": round(slope_delta, 6),
            "memory_wins": bool(overlay.get("memory_wins", False)),
            "overlay": str(overlay_path),
        },
    }
    print(json.dumps(report, indent=2))
    if not ok:
        sys.exit(1)
    print("CP5 memory A/B passed")


if __name__ == "__main__":
    main()