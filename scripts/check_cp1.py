#!/usr/bin/env python3
"""CP1 accuracy harness: Stim surface code + MWPM baseline."""

from __future__ import annotations

import json
import sys

from cryobrain.accuracy.stim_harness import surface_code_logical_error_rate


def main() -> int:
    low = surface_code_logical_error_rate(distance=3, noise_rate=0.001, shots=100, rounds=3)
    high = surface_code_logical_error_rate(distance=3, noise_rate=0.01, shots=100, rounds=3)
    print(json.dumps({"low_noise": low, "high_noise": high}, indent=2))
    ok = low["logical_error_rate"] < high["logical_error_rate"]
    ok = ok and low["logical_error_rate"] < 0.5
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())