"""PyMatching MWPM baseline decoder (SPEC F2)."""

from __future__ import annotations

import numpy as np
import pymatching
import stim


def decode_with_mwpm(circuit: stim.Circuit, detector_shots: np.ndarray) -> np.ndarray:
    """Decode detector shots with PyMatching; return observable flip predictions."""
    matcher = pymatching.Matching.from_stim_circuit(circuit)
    shots = np.asarray(detector_shots, dtype=np.uint8)
    return matcher.decode_batch(shots)


def mwpm_logical_error_rate(
    distance: int = 3,
    noise_rate: float = 0.001,
    shots: int = 1000,
    rounds: int = 3,
) -> float:
    """Convenience wrapper returning MWPM LER only."""
    from cryobrain.accuracy.stim_harness import surface_code_logical_error_rate

    return surface_code_logical_error_rate(
        distance=distance,
        noise_rate=noise_rate,
        shots=shots,
        rounds=rounds,
        decoder="mwpm",
    )["logical_error_rate"]