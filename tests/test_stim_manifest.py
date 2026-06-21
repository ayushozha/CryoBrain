"""G2: stim manifest splits."""

from __future__ import annotations

from cryobrain.stim.manifest import holdout_paths, load_manifest, manifest_checksum, split_config
from cryobrain.types import ScenarioConfig


def test_manifest_has_train_and_holdout(tmp_path):
    path = tmp_path / "manifest.json"
    data = load_manifest(path)
    assert "train" in data["splits"]
    assert "holdout" in data["splits"]
    assert data["checksum"] == manifest_checksum({k: v for k, v in data.items() if k != "checksum"})


def test_holdout_paths_non_empty(tmp_path):
    path = tmp_path / "manifest.json"
    load_manifest(path)
    assert len(holdout_paths(path)) > 0


def test_split_config_round_trip(tmp_path):
    path = tmp_path / "manifest.json"
    load_manifest(path)
    holdout = split_config("holdout", path)
    scenario = ScenarioConfig.from_dict(holdout["scenario"])
    assert scenario.distance in {3, 5, 7}