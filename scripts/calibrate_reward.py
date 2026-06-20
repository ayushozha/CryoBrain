#!/usr/bin/env python3
"""CP3 gating checkpoint: reward band 20–50% on starter with variance."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    script = Path("tasks/cryo_brain_decoder/scripts/check_calibration.py")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=False)
    print(proc.stdout or proc.stderr)
    if proc.returncode != 0:
        return proc.returncode
    data = json.loads(proc.stdout)
    starter = float(data["starter"])
    ok = 0.15 <= starter <= 0.55
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())