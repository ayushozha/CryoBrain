"""X9: baseline LER artifact schema and provenance guards."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

pytestmark = pytest.mark.wsl

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "artifacts" / "baselines" / "ler_baselines.json"
MANIFEST = ROOT / "tasks" / "cryo_brain_decoder" / "stim" / "manifest.json"
SCRIPT = ROOT / "scripts" / "compute_ler_baselines_wsl.sh"
DOC = ROOT / "docs" / "research" / "ECC_DECODER_METRICS.md"
FORBIDDEN = ("simulate_candidate_ler", "decoder_quality_multiplier", "candidate_ler")


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_baseline_artifact_schema_and_provenance():
    data = _json(BASELINES)
    manifest = _json(MANIFEST)

    assert data["schema_version"] == 1
    assert data["generated_by"] == "scripts/compute_ler_baselines_wsl.sh"
    assert isinstance(data["generated_at_utc"], str)
    assert data["source"] == {
        "kind": "mwpm_stim",
        "proxy_free": True,
        "decoder": "pymatching.Matching.from_stim_circuit",
        "sampler": "stim.CompiledDetectorSampler(seed=manifest split seed)",
    }
    assert data["stim_manifest"] == {
        "path": "tasks/cryo_brain_decoder/stim/manifest.json",
        "version": manifest["version"],
        "checksum": manifest["checksum"],
        "sha256": _sha256(MANIFEST),
    }
    assert isinstance(data["git"]["sha"], str) and len(data["git"]["sha"]) >= 7
    assert isinstance(data["git"]["branch"], str)
    assert isinstance(data["git"]["dirty"], bool)

    eps = data["reproducibility"]["epsilon_abs"]
    assert isinstance(eps, float)
    assert 0.0 <= eps <= 1.0


def test_baselines_match_manifest_and_are_real_rates():
    data = _json(BASELINES)
    manifest = _json(MANIFEST)
    rows = {row["split"]: row for row in data["baselines"]}

    assert set(rows) == set(manifest["splits"])
    assert all(token not in json.dumps(data) for token in FORBIDDEN)

    for split, cfg in manifest["splits"].items():
        row = rows[split]
        shots = int(row["shots"])
        logical_errors = int(row["logical_errors"])
        ler = float(row["logical_error_rate"])
        standard_error = float(row["standard_error"])
        epsilon_95 = float(row["epsilon_95"])

        assert row["decoder"] == "mwpm"
        assert row["scenario"] == cfg["scenario"]
        assert row["seed"] == cfg["seed"]
        assert row["manifest_vectors"] == cfg["vectors"]
        assert shots == cfg["scenario"]["shots"]
        assert 0 <= logical_errors <= shots
        assert math.isclose(ler, logical_errors / shots, rel_tol=0, abs_tol=1e-12)
        assert 0.0 <= ler <= 1.0
        assert math.isclose(
            standard_error,
            math.sqrt((ler * (1.0 - ler)) / shots),
            rel_tol=0,
            abs_tol=1e-12,
        )
        assert math.isclose(epsilon_95, 1.96 * standard_error, rel_tol=0, abs_tol=1e-12)


def test_runner_and_research_doc_keep_proxy_out_of_baselines():
    script = SCRIPT.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "surface_code_memory_circuit" in script
    assert "decode_with_mwpm" in script
    assert "Nature" in doc
    assert "Quantum 5, 497" in doc
    assert "PyMatching" in doc
    assert all(token not in script for token in FORBIDDEN)
