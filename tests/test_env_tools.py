"""Tests for expanded env.py agent tools."""

from __future__ import annotations

import json

import pytest

import env as env_module
from scenario_helpers import WORKSPACE_ROOT, setup_task


@pytest.mark.asyncio
async def test_get_scenario_reads_workspace():
    setup_task(
        "cryo_brain_decoder",
        scenario={"distance": 5, "noise_rate": 0.002},
    )
    raw = await env_module.get_scenario()
    payload = json.loads(raw)
    assert payload["distance"] == 5
    assert payload["noise_rate"] == 0.002


@pytest.mark.asyncio
async def test_get_design_config_reads_workspace():
    setup_task("cryo_brain_decoder")
    raw = await env_module.get_design_config()
    payload = json.loads(raw)
    assert "bitwidth" in payload
    assert "pipeline_depth" in payload


@pytest.mark.asyncio
async def test_update_design_config_merges_patch():
    setup_task("cryo_brain_decoder")
    env_module._last_observation = {"task_id": "cryo_brain_decoder"}
    patch = json.dumps({"parallelism": 2, "pipeline_depth": 8})
    raw = await env_module.update_design_config(patch)
    payload = json.loads(raw)
    assert payload["parallelism"] == 2
    assert payload["pipeline_depth"] == 8

    on_disk = json.loads((WORKSPACE_ROOT / "design_config.json").read_text(encoding="utf-8"))
    assert on_disk["parallelism"] == 2


@pytest.mark.asyncio
async def test_run_eval_returns_breakdown():
    setup_task("cryo_brain_decoder")
    env_module._last_observation = {"task_id": "cryo_brain_decoder", "slug": "cryo-brain-decoder-d3"}
    raw = await env_module.run_eval()
    payload = json.loads(raw)
    assert "reward" in payload
    assert "hard_caps" in payload
    assert "rtl_validity" in payload
    assert "ler_suppression" in payload

    obs = json.loads(await env_module.get_observation())
    assert obs.get("last_eval") is not None
    assert obs["last_eval"]["reward"] == payload["reward"]


def test_agent_eval_payload_strips_hidden_logs():
    result = {
        "reward": 0.42,
        "hard_caps": [],
        "subscores": {
            "rtl_validity": {"result": {"sim": True, "lint": True}},
            "ler_suppression": {"raw_score": 0.3, "result": {"mwpm_ler": 0.02}},
            "latency": {"result": {"latency_cycles": 12}},
            "area": {"result": {"area_mm2": 0.04}},
        },
        "info": {"rtl_logs": {"secret": "hidden"}},
    }
    payload = env_module._agent_eval_payload(result)
    assert payload["reward"] == 0.42
    assert "rtl_logs" not in payload
    assert payload["ler_suppression"]["score"] == 0.3