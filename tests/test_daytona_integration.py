"""C7: Daytona per-variant sandbox measurement (SPEC-v5).

Offline (always runs): the integration imports, ``measure_in_sandbox`` has the
documented signature, and it clean-skips (raises, never fabricates) when the SDK
or key is missing. Live (key + SDK + Linux/WSL): create -> measure -> destroy a
real sandbox and assert the result carries MeasureResult fields. On Windows
without the native SDK/key, the live test skips.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from cryobrain.integrations.daytona import daytona_available, daytona_sandbox
from cryobrain.sandbox import measure_in_sandbox
from cryobrain.types import ScenarioConfig

_RESULT_FIELDS = (
    "candidate_ler",
    "mwpm_ler",
    "suppression",
    "shots",
    "vector_source",
    "rtl_path",
    "benchmark_vectors",
    "benchmark_failures",
    "rtl_valid",
)

_CANDIDATE_RTL = (
    Path(__file__).resolve().parents[1]
    / "tasks"
    / "cryo_brain_decoder"
    / "rtl"
    / "cryo_brain_decoder.sv"
)


# --- Offline contract (no key / no SDK needed) ------------------------------


def test_measure_in_sandbox_importable_and_callable():
    assert callable(measure_in_sandbox)
    assert callable(daytona_sandbox)
    assert callable(daytona_available)


def test_measure_in_sandbox_signature():
    sig = inspect.signature(measure_in_sandbox)
    params = sig.parameters
    assert list(params)[:2] == ["rtl_path", "scenario"]
    # Documented keyword-only knobs with their defaults.
    assert params["shots"].default == 1000
    assert params["seed"].default == 0
    assert params["benchmark_vectors"].default == 64
    for kw in ("shots", "seed", "benchmark_vectors", "timeout_sec"):
        assert params[kw].kind == inspect.Parameter.KEYWORD_ONLY


def test_clean_skip_without_key(monkeypatch):
    """Without an available SDK/key the call raises rather than faking a result."""
    monkeypatch.setattr(
        "cryobrain.sandbox.measure_runner.daytona_available", lambda: False
    )
    with pytest.raises(RuntimeError, match="unavailable"):
        measure_in_sandbox(_CANDIDATE_RTL, ScenarioConfig())


def test_daytona_available_false_without_key(monkeypatch):
    monkeypatch.setattr("cryobrain.integrations.daytona.get_key", lambda name: None)
    assert daytona_available() is False


# --- Live path (real sandbox; needs key + SDK + Linux EDA) ------------------


@pytest.mark.wsl
@pytest.mark.skipif(
    not daytona_available(),
    reason="Daytona SDK + DAYTONA_API_KEY required (install in WSL/Linux)",
)
def test_live_create_measure_destroy():
    """Real sandbox round-trip: create -> measure -> destroy, real result shape."""
    result = measure_in_sandbox(_CANDIDATE_RTL, ScenarioConfig(distance=3, noise_rate=0.02))
    for field in _RESULT_FIELDS:
        assert field in result, f"missing MeasureResult field: {field}"
    assert isinstance(result["candidate_ler"], (int, float))
    assert isinstance(result["mwpm_ler"], (int, float))
    assert 0.0 <= float(result["candidate_ler"]) <= 1.0


@pytest.mark.wsl
@pytest.mark.skipif(
    not daytona_available(),
    reason="Daytona SDK + DAYTONA_API_KEY required (install in WSL/Linux)",
)
def test_live_sandbox_lifecycle_destroys_on_error():
    """The sandbox context manager deletes even when the body raises."""
    deleted = {"called": False}

    with pytest.raises(ValueError):
        with daytona_sandbox() as sandbox:
            original_delete = sandbox.delete

            def _tracking_delete(*a, **k):
                deleted["called"] = True
                return original_delete(*a, **k)

            sandbox.delete = _tracking_delete  # type: ignore[method-assign]
            raise ValueError("boom")
    assert deleted["called"] is True
