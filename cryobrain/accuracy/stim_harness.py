"""Stim-based surface-code accuracy harness (SPEC F1)."""

from __future__ import annotations

import numpy as np
import stim

from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm
from cryobrain.types import DesignConfig, ScenarioConfig

SUPPORTED_DISTANCES = frozenset({3, 5, 7})


def surface_code_memory_circuit(
    distance: int = 3,
    noise_rate: float = 0.001,
    rounds: int = 3,
) -> stim.Circuit:
    """Build a rotated surface-code memory experiment circuit."""
    if distance not in SUPPORTED_DISTANCES:
        raise ValueError(f"unsupported distance {distance}; expected 3, 5, or 7")
    if noise_rate < 0:
        raise ValueError("noise_rate must be non-negative")
    if rounds < 1:
        raise ValueError("rounds must be >= 1")
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
    if shots < 1:
        raise ValueError("shots must be >= 1")
    sampler = circuit.compile_detector_sampler()
    dets, obs = sampler.sample(shots, separate_observables=True)
    return np.asarray(dets, dtype=np.uint8), np.asarray(obs, dtype=np.uint8)


def count_logical_errors(predictions: np.ndarray, observables: np.ndarray) -> int:
    """Count shots where any logical observable prediction disagrees with truth."""
    pred = np.asarray(predictions, dtype=np.uint8)
    obs = np.asarray(observables, dtype=np.uint8)
    if pred.ndim == 1:
        pred = pred.reshape(-1, 1)
    if obs.ndim == 1:
        obs = obs.reshape(-1, 1)
    if pred.shape[0] != obs.shape[0]:
        raise ValueError(
            f"prediction/observable shot count mismatch: {pred.shape[0]} vs {obs.shape[0]}"
        )
    width = min(pred.shape[1], obs.shape[1])
    if width == 0:
        return 0
    return int(np.sum(np.any(pred[:, :width] != obs[:, :width], axis=1)))


def logical_error_rate_from_predictions(
    predictions: np.ndarray,
    observables: np.ndarray,
    shots: int,
) -> float:
    """LER estimate from decode predictions and sampled observables."""
    errors = count_logical_errors(predictions, observables)
    return errors / max(int(shots), 1)


def surface_code_logical_error_rate(
    distance: int = 3,
    noise_rate: float = 0.001,
    shots: int = 1000,
    rounds: int = 3,
    decoder: str = "mwpm",
    *,
    design: DesignConfig | None = None,
    rtl_valid: bool = True,
) -> dict[str, float]:
    """Sample shots and estimate logical error rate (LER).

    ``decoder`` options:
    - ``mwpm``: real PyMatching decode on Stim shots.
    - ``policy``: removed in SPEC-v5; use measured RTL scoring for candidates.
    """
    circuit = surface_code_memory_circuit(distance, noise_rate, rounds)
    dets, obs = sample_shots(circuit, shots)

    from cryobrain.accuracy.mwpm_baseline import decode_with_mwpm

    predictions = decode_with_mwpm(circuit, dets)
    mwpm_ler = logical_error_rate_from_predictions(predictions, obs, shots)

    if decoder == "mwpm":
        ler = mwpm_ler
    elif decoder == "policy":
        raise ValueError("policy decoder proxy was removed; use measure_candidate_ler")
    else:
        raise ValueError(f"unsupported decoder {decoder!r}; expected 'mwpm' or 'policy'")

    suppression = ler_suppression_vs_mwpm(ler, mwpm_ler) if decoder == "policy" else (
        ler_suppression_vs_mwpm(mwpm_ler, mwpm_ler) if mwpm_ler > 0 else 0.0
    )

    return {
        "distance": float(distance),
        "noise_rate": noise_rate,
        "shots": float(shots),
        "rounds": float(rounds),
        "logical_errors": float(count_logical_errors(predictions, obs)),
        "logical_error_rate": ler,
        "mwpm_logical_error_rate": mwpm_ler,
        "ler_suppression_vs_mwpm": suppression,
        "physical_error_rate": noise_rate,
        "decoder": decoder,
    }


def evaluate_accuracy(
    scenario: ScenarioConfig,
    design: DesignConfig,
    *,
    rtl_valid: bool = True,
) -> dict[str, float]:
    """Fail-closed accuracy snapshot until measured RTL scoring is wired."""
    stats = surface_code_logical_error_rate(
        distance=scenario.distance,
        noise_rate=scenario.noise_rate,
        shots=scenario.shots,
        rounds=scenario.rounds,
        decoder="mwpm",
    )
    mwpm_ler = float(stats["logical_error_rate"])
    candidate_ler = mwpm_ler
    _ = design, rtl_valid
    return {
        **stats,
        "decoder": "mwpm_fail_closed",
        "candidate_ler": candidate_ler,
        "mwpm_ler": mwpm_ler,
        "ler_suppression_vs_mwpm": ler_suppression_vs_mwpm(candidate_ler, mwpm_ler),
    }
