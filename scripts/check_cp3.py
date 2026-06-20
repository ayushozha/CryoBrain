#!/usr/bin/env python3
"""CP3 checkpoint entry: delegates to calibrate_reward with WSL fallback."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    script = ROOT / "scripts" / "calibrate_reward.py"
    return subprocess.run([sys.executable, str(script)], cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())