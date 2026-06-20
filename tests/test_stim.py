from cryobrain.accuracy.stim_harness import surface_code_memory_circuit, surface_code_logical_error_rate


def test_surface_code_circuit_builds():
    circuit = surface_code_memory_circuit(distance=3, noise_rate=0.001, rounds=3)
    assert circuit.num_detectors > 0


def test_ler_increases_with_noise():
    low = surface_code_logical_error_rate(distance=3, noise_rate=0.001, shots=50, rounds=3)
    high = surface_code_logical_error_rate(distance=3, noise_rate=0.01, shots=50, rounds=3)
    assert high["logical_error_rate"] >= low["logical_error_rate"]