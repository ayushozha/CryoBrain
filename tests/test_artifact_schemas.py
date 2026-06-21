import pytest

from cryobrain.artifacts.schemas.v2 import (
    ArtifactSchemaError,
    validate_measured_climb,
    validate_measured_memory_ab,
    validate_pareto,
)


def test_validate_measured_climb_accepts_required_fields():
    artifact = {
        "history": [
            {"step": 1, "candidate_ler": 0.17, "suppression": 0.2, "rtl_hash": "abc123"}
        ]
    }
    assert validate_measured_climb(artifact) is artifact


def test_validate_measured_climb_rejects_proxy_field():
    artifact = {
        "history": [
            {
                "step": 1,
                "candidate_ler": 0.17,
                "suppression": 0.2,
                "rtl_hash": "abc123",
                "decoder_quality_multiplier": 0.82,
            }
        ]
    }
    with pytest.raises(ArtifactSchemaError, match="proxy field"):
        validate_measured_climb(artifact)


def test_validate_pareto_accepts_required_fields():
    artifact = {
        "points": [
            {
                "label": "golden",
                "ler": 0.02,
                "area_um2": 6.1,
                "latency_cycles": 8,
                "rtl_path": "artifacts/variants/golden.sv",
            }
        ]
    }
    assert validate_pareto(artifact) is artifact


def test_validate_memory_ab_accepts_two_measured_series():
    row = {"step": 0, "candidate_ler": 0.2, "suppression": 0.0, "rtl_hash": "abc123"}
    artifact = {"with_memory": [row], "without_memory": [row]}
    assert validate_measured_memory_ab(artifact) is artifact


def test_validate_pareto_rejects_missing_required_field():
    artifact = {"points": [{"label": "bad", "ler": 0.02, "area_um2": 6.1, "rtl_path": "x.sv"}]}
    with pytest.raises(ArtifactSchemaError, match="latency_cycles"):
        validate_pareto(artifact)
