"""Stim-based surface-code accuracy harness (SPEC F1)."""

from __future__ import annotations

import numpy as np
import stim


def surface_code_memory_circuit(
    distance: int = 3,
    noise_rate: float = 0.001,
    rounds: int = 3,
) -> stim.Circuit:
    """Build a rotated surface-code memory experiment circuit."""
    if distance not in {3, 5, 7}:
        raise ValueError(f"unsupported distance {distance}; expected 3, 5, or 7")
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=distance,
        rounds=rounds,
        after_clifford_depolarization=noise_rate,
        after_reset_flip_probability=noise_rate,
        before_measure_flip_probability=noise_rate,
        before_round_data_depolarization=noise_rate,
    )


def sample_shots(circuit: stim.Circuit, shots: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (detector_shots, observable_shots) as uint8 arrays."""
    sampler = circuit.compile_detector_sampler()
    dets, obs = sampler.sample(shots, separate_observables=True)
    return np.asarray(dets, dtype=np.uint8), np.asarray(obs, dtype=np.uint8)


def surface_code_logical_error_rate(
    distance: int = 3,
    noise_rate: float = 0.001,
    shots: int = 1000,
    rounds: int = 3,
    decoder: str = "mwpm",
) -> dict[str, float]:
    """Sample shots and estimate logical error rate (LER)."""
    circuit = surface_code_memory_circuit(distance, noise_rate, rounds)
    dets, obs = sample_shots(circuit, shots)

    if decoder == "mwpm":
        from cryobrain.accuracy.mwpm_baseline import decode_with_mwpm

        predictions = decode_with_mwpm(circuit, dets)
    else:
        raise ValueError(f"unsupported decoder {decoder!r}")

    num_errors = int(np.sum(np.any(predictions != obs, axis=1)))
    ler = num_errors / max(shots, 1)
    return {
        "distance": float(distance),
        "noise_rate": noise_rate,
        "shots": float(shots),
        "logical_errors": float(num_errors),
        "logical_error_rate": ler,
        "physical_error_rate": noise_rate,
    }