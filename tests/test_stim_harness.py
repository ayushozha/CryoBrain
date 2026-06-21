from cryobrain.accuracy.benchmark_vectors import generate_rtl_benchmark
from cryobrain.stim.compare import compare_corrections
from cryobrain.types import ScenarioConfig


def test_stim_benchmark_compare_is_deterministic():
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=16, rounds=3)
    benchmark = generate_rtl_benchmark(scenario, vectors=16, seed=1729)
    expected = [correction for _syndrome, correction in benchmark.vectors]

    first = compare_corrections(expected, expected)
    second = compare_corrections(expected, expected)

    assert first == second
    assert first.total == 16
    assert first.mismatches == 0
    assert first.exactness == 1.0


def test_stim_benchmark_compare_detects_wrong_corrections():
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=16, rounds=3)
    benchmark = generate_rtl_benchmark(scenario, vectors=16, seed=1729)
    expected = [correction for _syndrome, correction in benchmark.vectors]
    observed = [value ^ 0x1 for value in expected]

    result = compare_corrections(expected, observed)

    assert result.total == 16
    assert result.mismatches == 16
    assert result.exactness == 0.0
