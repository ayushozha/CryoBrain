"""Stim-backed RTL benchmark vectors for the CP2 validity gate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cryobrain.accuracy.stim_harness import surface_code_memory_circuit
from cryobrain.types import ScenarioConfig


@dataclass(frozen=True)
class RtlBenchmark:
    metadata: dict[str, int | float | str]
    vectors: list[tuple[int, int]]


def _pack_bits_lsb_first(bits: np.ndarray) -> int:
    value = 0
    for idx, bit in enumerate(bits[:8]):
        value |= int(bit) << idx
    return value


def _reference_correction(syndrome: int) -> int:
    return (syndrome & 0xF) ^ ((syndrome >> 4) & 0xF)


def generate_rtl_benchmark(
    scenario: ScenarioConfig,
    *,
    vectors: int = 64,
    seed: int = 1729,
    min_noise_rate: float = 0.02,
) -> RtlBenchmark:
    """Generate a deterministic, stratified RTL benchmark from real Stim shots.

    CP2 only verifies the tiny RTL policy against realistic syndrome traffic; it
    does not claim these 8-bit windows are a full neural QEC decoder. The
    stratification keeps the benchmark from being dominated by all-zero windows
    at low physical error rates.
    """
    if vectors < 1:
        raise ValueError("vectors must be >= 1")
    noise_rate = max(scenario.noise_rate, min_noise_rate)
    circuit = surface_code_memory_circuit(scenario.distance, noise_rate, scenario.rounds)
    sampler = circuit.compile_detector_sampler(seed=seed)
    pool_shots = max(scenario.shots, vectors * 8)
    dets, obs = sampler.sample(pool_shots, separate_observables=True)

    hard: list[tuple[int, int]] = []
    active: list[tuple[int, int]] = []
    quiet: list[tuple[int, int]] = []
    for row in np.asarray(dets, dtype=np.uint8):
        for offset in range(0, len(row) - 7, 8):
            syndrome = _pack_bits_lsb_first(row[offset : offset + 8])
            expected = _reference_correction(syndrome)
            item = (syndrome, expected)
            if expected != ((syndrome & 0xF) | ((syndrome >> 4) & 0xF)):
                hard.append(item)
            elif syndrome:
                active.append(item)
            else:
                quiet.append(item)

    target_hard = vectors // 2
    selected = hard[:target_hard]
    selected.extend(active[: max(0, vectors - len(selected))])
    selected.extend(quiet[: max(0, vectors - len(selected))])
    selected = selected[:vectors]
    if len(selected) < vectors:
        raise RuntimeError(f"only generated {len(selected)} benchmark vectors")

    metadata = {
        "source": "Stim surface_code:rotated_memory_z detector samples",
        "reference": "Gidney 2021 Stim; PyMatching/MWPM remains the CP3 LER anchor",
        "distance": scenario.distance,
        "rounds": scenario.rounds,
        "noise_rate": noise_rate,
        "seed": seed,
        "pool_shots": pool_shots,
        "num_detectors": circuit.num_detectors,
        "num_observables": circuit.num_observables,
        "observable_ones": int(np.sum(obs)),
        "vectors": len(selected),
        "hard_vectors": min(len(hard), target_hard),
        "active_vectors": sum(1 for syndrome, _ in selected if syndrome),
    }
    return RtlBenchmark(metadata=metadata, vectors=selected)


def write_rtl_benchmark(path: Path, benchmark: RtlBenchmark) -> Path:
    """Write Verilator-readable vectors as ``<syndrome_hex> <expected_hex>``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{syndrome:02x} {expected:x}" for syndrome, expected in benchmark.vectors)
    path.write_text(f"{body}\n", encoding="utf-8")
    return path
