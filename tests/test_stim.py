import numpy as np
import pytest

from cryobrain.accuracy.benchmark_vectors import generate_rtl_benchmark, write_rtl_benchmark
from cryobrain.accuracy.mwpm_baseline import decode_with_mwpm
from cryobrain.accuracy.stim_harness import (
    count_logical_errors,
    evaluate_accuracy,
    sample_shots,
    surface_code_memory_circuit,
    surface_code_logical_error_rate,
)
from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm
from cryobrain.types import DesignConfig, ScenarioConfig


def test_surface_code_circuit_builds_for_all_distances():
    for distance in (3, 5, 7):
        circuit = surface_code_memory_circuit(distance=distance, noise_rate=0.001, rounds=3)
        assert circuit.num_detectors > 0


def test_sample_shots_returns_uint8_separate_observables():
    circuit = surface_code_memory_circuit(distance=3, noise_rate=0.001, rounds=3)
    dets, obs = sample_shots(circuit, shots=8)
    assert dets.dtype == np.uint8
    assert obs.dtype == np.uint8
    assert dets.ndim == 2
    assert obs.ndim == 2
    assert dets.shape[0] == 8


def test_rtl_benchmark_uses_real_stim_detector_windows(tmp_path):
    scenario = ScenarioConfig(distance=3, noise_rate=0.001, shots=16, rounds=3)
    benchmark = generate_rtl_benchmark(scenario, vectors=16, seed=1234)
    assert benchmark.metadata["source"] == "Stim surface_code:rotated_memory_z detector samples"
    assert benchmark.metadata["hard_vectors"] > 0
    assert len(benchmark.vectors) == 16
    assert all(0 <= syndrome <= 0xFF and 0 <= expected <= 0xF for syndrome, expected in benchmark.vectors)

    vector_path = write_rtl_benchmark(tmp_path / "stim_vectors.mem", benchmark)
    lines = vector_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 16
    assert all(len(line.split()) == 2 for line in lines)


def test_mwpm_decode_accepts_uint8_detectors():
    circuit = surface_code_memory_circuit(distance=3, noise_rate=0.001, rounds=3)
    dets, _obs = sample_shots(circuit, shots=4)
    predictions = decode_with_mwpm(circuit, dets)
    assert predictions.dtype == np.uint8 or predictions.dtype == np.bool_


def test_ler_increases_with_noise():
    low = surface_code_logical_error_rate(distance=3, noise_rate=0.001, shots=50, rounds=3)
    high = surface_code_logical_error_rate(distance=3, noise_rate=0.01, shots=50, rounds=3)
    assert high["logical_error_rate"] >= low["logical_error_rate"]
    assert low["mwpm_logical_error_rate"] == low["logical_error_rate"]


def test_mwpm_suppresses_physical_rate_at_low_noise():
    stats = surface_code_logical_error_rate(distance=3, noise_rate=0.001, shots=80, rounds=3)
    assert stats["logical_error_rate"] < stats["physical_error_rate"]


def test_count_logical_errors_handles_1d_observables():
    preds = np.array([0, 1, 0], dtype=np.uint8)
    obs = np.array([0, 0, 1], dtype=np.uint8)
    assert count_logical_errors(preds, obs) == 2


def test_ler_suppression_vs_mwpm_metric():
    assert ler_suppression_vs_mwpm(0.01, 0.02) == 0.5
    assert ler_suppression_vs_mwpm(0.03, 0.02) == 0.0
    assert ler_suppression_vs_mwpm(0.0, 0.02) == 1.0


def test_policy_decoder_proxy_is_removed():
    with pytest.raises(ValueError, match="policy decoder proxy was removed"):
        surface_code_logical_error_rate(
            distance=3,
            noise_rate=0.008,
            shots=120,
            rounds=3,
            decoder="policy",
            design=DesignConfig(),
            rtl_valid=True,
        )


def test_evaluate_accuracy_no_longer_rewards_design_knobs():
    scenario = ScenarioConfig(distance=3, noise_rate=0.008, shots=120, rounds=3)
    weak = DesignConfig(bitwidth=2, num_layers=1, window_length=4)
    strong = DesignConfig(bitwidth=8, num_layers=4, window_length=16, parallelism=2)

    weak_stats = evaluate_accuracy(scenario, weak, rtl_valid=True)
    strong_stats = evaluate_accuracy(scenario, strong, rtl_valid=True)

    assert weak_stats["candidate_ler"] == weak_stats["mwpm_ler"]
    assert strong_stats["candidate_ler"] == strong_stats["mwpm_ler"]
    assert weak_stats["ler_suppression_vs_mwpm"] == 0.0
    assert strong_stats["ler_suppression_vs_mwpm"] == 0.0


def test_evaluate_accuracy_end_to_end():
    scenario = ScenarioConfig(distance=5, noise_rate=0.001, shots=30, rounds=3)
    design = DesignConfig(bitwidth=8, num_layers=3)
    result = evaluate_accuracy(scenario, design, rtl_valid=True)
    assert result["distance"] == 5.0
    assert result["candidate_ler"] == result["mwpm_ler"]
    assert result["ler_suppression_vs_mwpm"] == ler_suppression_vs_mwpm(
        result["candidate_ler"], result["mwpm_ler"]
    )
