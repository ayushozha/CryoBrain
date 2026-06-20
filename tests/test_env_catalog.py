"""Integration tests for HUD task catalog, curriculum, and env tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import env as env_module
from scenario_helpers import WORKSPACE_ROOT, setup_task
from task_catalog import (
    CRYO_CURRICULUM,
    CRYO_SLUGS,
    FALLBACK_SLUGS,
    TASK_SPECS,
    TASK_SPECS_BY_SLUG,
    TASK_SPECS_BY_TASK_ID,
    curriculum_for_slug,
)


def test_catalog_has_six_eval_variants():
    assert len(TASK_SPECS) == 6
    assert len(TASK_SPECS_BY_SLUG) == 6
    slugs = [spec.slug for spec in TASK_SPECS]
    assert len(slugs) == len(set(slugs))


def test_catalog_tracks_cryo_and_fallback():
    cryo = [spec for spec in TASK_SPECS if spec.track == "qec-codesign"]
    fallback = [spec for spec in TASK_SPECS if spec.track.startswith("fallback")]
    assert len(cryo) == 3
    assert len(fallback) == 3
    assert tuple(spec.slug for spec in cryo) == CRYO_SLUGS
    assert FALLBACK_SLUGS == (
        "stream-arb-fifo-repair",
        "stream-arb-fifo-cocotb-dv",
        "stream-arb-fifo-formal",
    )


def test_rsi_curriculum_distances_d3_d5_d7():
    assert CRYO_CURRICULUM["cryo-brain-decoder-d3"]["distance"] == 3
    assert CRYO_CURRICULUM["cryo-brain-decoder-d5"]["distance"] == 5
    assert CRYO_CURRICULUM["cryo-brain-decoder-d7"]["distance"] == 7
    for slug in CRYO_SLUGS:
        knobs = curriculum_for_slug(slug)
        assert knobs["distance"] == CRYO_CURRICULUM[slug]["distance"]
        assert knobs["noise_rate"] == CRYO_CURRICULUM[slug]["noise_rate"]


def test_task_id_index_is_unique_per_filesystem_task():
    assert len(TASK_SPECS_BY_TASK_ID) == 4
    assert "cryo_brain_decoder" in TASK_SPECS_BY_TASK_ID
    assert TASK_SPECS_BY_TASK_ID["cryo_brain_decoder"].slug == "cryo-brain-decoder-d3"


def test_tasks_py_binds_six_hud_tasks():
    import tasks as tasks_module

    bound_slugs = [task.slug for task in tasks_module.tasks]
    assert len(bound_slugs) == 6
    assert set(bound_slugs) == set(TASK_SPECS_BY_SLUG)


@pytest.mark.parametrize(
    "slug,expected_distance",
    [
        ("cryo-brain-decoder-d3", 3),
        ("cryo-brain-decoder-d5", 5),
        ("cryo-brain-decoder-d7", 7),
    ],
)
def test_setup_injects_curriculum_scenario(slug: str, expected_distance: int):
    knobs = curriculum_for_slug(slug)
    setup_task(
        "cryo_brain_decoder",
        scenario={
            "distance": knobs["distance"],
            "noise_rate": knobs["noise_rate"],
            "max_latency_cycles": knobs["max_latency_cycles"],
            "max_area_mm2": knobs["max_area_mm2"],
            "max_power_mw": knobs["max_power_mw"],
        },
    )
    scenario_path = WORKSPACE_ROOT / "scenario.json"
    assert scenario_path.is_file()
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    assert scenario["distance"] == expected_distance
    assert scenario["max_latency_cycles"] == knobs["max_latency_cycles"]


@pytest.mark.asyncio
async def test_get_observation_returns_json():
    env_module._last_observation = {
        "slug": "cryo-brain-decoder-d3",
        "distance": 3,
        "noise_rate": 0.001,
    }
    raw = await env_module.get_observation()
    payload = json.loads(raw)
    assert payload["slug"] == "cryo-brain-decoder-d3"
    assert payload["distance"] == 3


@pytest.mark.asyncio
async def test_run_eval_preview_returns_preview_payload():
    setup_task("cryo_brain_decoder")
    rtl = WORKSPACE_ROOT / "rtl" / "cryo_brain_decoder.sv"
    assert rtl.is_file()

    env_module._last_observation = {"slug": "cryo-brain-decoder-d3", "task_id": "cryo_brain_decoder"}
    raw = await env_module.run_eval_preview()
    payload = json.loads(raw)
    for key in ("sim_passed", "synth_passed", "lint_passed", "cell_count"):
        assert key in payload

    obs = json.loads(await env_module.get_observation())
    assert obs["last_preview"] is not None
    assert obs["last_preview"]["lint_passed"] == payload["lint_passed"]