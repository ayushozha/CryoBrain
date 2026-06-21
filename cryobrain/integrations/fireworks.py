"""Fireworks inference for design proposals (SPEC2 F6 rollout helper)."""

from __future__ import annotations

import json
import re
from typing import Any

from cryobrain.integrations.secrets import get_key
from cryobrain.types import DesignConfig

FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
DEFAULT_MODEL = "accounts/fireworks/models/deepseek-v3p1"


def _parse_design_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def propose_design_config(
    *,
    scenario: dict[str, Any],
    exemplars: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
) -> DesignConfig | None:
    """Ask Fireworks for a design_config patch; None when API unavailable."""
    api_key = get_key("FIREWORKS_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=api_key, base_url=FIREWORKS_BASE)
    prompt = {
        "task": "Propose cryo_brain_decoder design_config JSON knobs only.",
        "scenario": scenario,
        "exemplars": exemplars[:3],
        "schema": {
            "bitwidth": "2|4|8",
            "num_layers": "1-4",
            "parallelism": "1-4",
            "pipeline_depth": "2-16",
            "window_length": "4-16",
        },
    }
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return ONLY one JSON object with keys: bitwidth, num_layers, "
                        "parallelism, pipeline_depth, window_length. Integers only."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.4,
            max_tokens=256,
        )
    except Exception:
        return None

    text = completion.choices[0].message.content or ""
    payload = _parse_design_json(text)
    if not payload:
        return None
    try:
        return DesignConfig(
            bitwidth=int(payload.get("bitwidth", 4)),
            num_layers=int(payload.get("num_layers", 1)),
            parallelism=int(payload.get("parallelism", 1)),
            pipeline_depth=int(payload.get("pipeline_depth", 4)),
            window_length=int(payload.get("window_length", 8)),
        )
    except (TypeError, ValueError):
        return None