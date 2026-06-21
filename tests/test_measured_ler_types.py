"""G1: measure_candidate_ler API surface."""

from __future__ import annotations

import inspect
from pathlib import Path

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.accuracy.types import MeasureResult
from cryobrain.types import ScenarioConfig


def test_measure_candidate_ler_signature():
    sig = inspect.signature(measure_candidate_ler)
    assert "rtl_path" in sig.parameters
    assert "scenario" in sig.parameters
    assert sig.parameters["shots"].default == 1000
    assert sig.parameters["seed"].default == 0


def test_measure_result_keys():
    hints = MeasureResult.__annotations__
    for key in (
        "candidate_ler",
        "mwpm_ler",
        "suppression",
        "shots",
        "vector_source",
        "rtl_path",
        "benchmark_vectors",
        "benchmark_failures",
        "rtl_valid",
    ):
        assert key in hints


def test_measure_candidate_ler_importable():
    assert callable(measure_candidate_ler)
    assert ScenarioConfig is not None
    assert Path is not None