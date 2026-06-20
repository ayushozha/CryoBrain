#!/usr/bin/env python3
"""CP1 accuracy harness: Stim surface code + MWPM baseline."""

from __future__ import annotations

import json
import sys

from cryobrain.accuracy.stim_harness import surface_code_logical_error_rate
from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm


def main() -> int:
    low = surface_code_logical_error_rate(distance=3, noise_rate=0.001, shots=100, rounds=3)
    high = surface_code_logical_error_rate(distance=3, noise_rate=0.01, shots=100, rounds=3)

    # MWPM should suppress physical noise at low error rates (CP1 sanity).
    suppression_visible = low["logical_error_rate"] < low["physical_error_rate"]
    monotonic = low["logical_error_rate"] < high["logical_error_rate"]
    bounded = low["logical_error_rate"] < 0.5

    # Spot-check d=5 and d=7 circuit wiring (fast, few shots).
    d5 = surface_code_logical_error_rate(distance=5, noise_rate=0.001, shots=20, rounds=3)
    d7 = surface_code_logical_error_rate(distance=7, noise_rate=0.001, shots=20, rounds=3)
    distances_ok = d5["distance"] == 5.0 and d7["distance"] == 7.0

    payload = {
        "low_noise": low,
        "high_noise": high,
        "d5": d5,
        "d7": d7,
        "checks": {
            "ler_rises_with_noise": monotonic,
            "mwpm_suppresses_physical_rate": suppression_visible,
            "low_noise_ler_bounded": bounded,
            "distances_supported": distances_ok,
            "mwpm_self_suppression_zero": ler_suppression_vs_mwpm(
                low["logical_error_rate"], low["logical_error_rate"]
            )
            == 0.0,
        },
    }
    print(json.dumps(payload, indent=2))

    ok = all(payload["checks"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())