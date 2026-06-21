"""Fireworks inference for design proposals (SPEC-v5 C2, OpenAI-compatible).

Real Fireworks API only. The model output is *never* trusted raw: every
proposal is validated against ``validate_design`` before it leaves this
module (trust boundary). No mocked/fake responses live in this path —
without ``FIREWORKS_API_KEY`` the low-level proposer returns ``None`` so
callers (and tests) can skip cleanly.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from cryobrain.design.validators import validate_design
from cryobrain.integrations.secrets import get_key
from cryobrain.types import DesignConfig

FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
# Serverless, JSON-mode-capable, available on the project account. Reasoning
# models (gpt-oss) emit reasoning before the answer, so leave generous tokens.
DEFAULT_MODEL = "accounts/fireworks/models/gpt-oss-20b"

# DesignConfig field bounds, kept in sync with cryobrain.design.validators.
# Used to coerce model output into the legal space before validation.
_BITWIDTH = (2, 4, 8)
_PARALLELISM = (1, 2, 4)
_DEFAULTS = DesignConfig()

_SYSTEM_PROMPT = (
    "You design a cryogenic surface-code decoder (cryo_brain_decoder). "
    "Return ONLY one JSON object, no prose, with exactly these integer keys: "
    "bitwidth (one of 2, 4, 8), num_layers (1-8), parallelism (one of 1, 2, 4), "
    "pipeline_depth (1-16), window_length (4-32). "
    "Propose a config likely to lower the measured logical error rate while "
    "staying inside a cryo area/latency budget. Integers only."
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a single JSON object from model text.

    Tries (1) the whole string, (2) a fenced ```json block, (3) the first
    brace-balanced span. Handles nested braces, unlike a naive ``\\{[^{}]*\\}``.
    """
    text = text.strip()
    for candidate in _json_candidates(text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _json_candidates(text: str):
    yield text
    fenced = _FENCE_RE.search(text)
    if fenced:
        yield fenced.group(1)
    span = _first_balanced_object(text)
    if span is not None:
        yield span


def _first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _coerce_to_legal(payload: dict[str, Any]) -> DesignConfig | None:
    """Coerce a raw dict into a *legal* DesignConfig, or None if it cannot.

    Snap to nearest allowed value for discrete knobs and clamp ranged knobs,
    then run the authoritative ``validate_design`` as the final gate. We never
    return a config that fails validation.
    """
    try:
        bitwidth = _nearest(int(payload.get("bitwidth", _DEFAULTS.bitwidth)), _BITWIDTH)
        parallelism = _nearest(int(payload.get("parallelism", _DEFAULTS.parallelism)), _PARALLELISM)
        num_layers = _clamp(int(payload.get("num_layers", _DEFAULTS.num_layers)), 1, 8)
        pipeline_depth = _clamp(int(payload.get("pipeline_depth", _DEFAULTS.pipeline_depth)), 1, 16)
        window_length = _clamp(int(payload.get("window_length", _DEFAULTS.window_length)), 4, 32)
    except (TypeError, ValueError):
        return None

    design = DesignConfig(
        bitwidth=bitwidth,
        num_layers=num_layers,
        parallelism=parallelism,
        pipeline_depth=pipeline_depth,
        window_length=window_length,
    )
    try:
        validate_design(design)
    except ValueError:
        return None
    return design


def _nearest(value: int, allowed: tuple[int, ...]) -> int:
    return min(allowed, key=lambda a: abs(a - value))


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _build_user_prompt(scenario: dict[str, Any], exemplars: list[dict[str, Any]]) -> str:
    return json.dumps(
        {
            "task": "Propose cryo_brain_decoder design_config JSON knobs only.",
            "scenario": scenario,
            "best_so_far": exemplars[:3],
            "schema": {
                "bitwidth": "2|4|8",
                "num_layers": "1-8",
                "parallelism": "1|2|4",
                "pipeline_depth": "1-16",
                "window_length": "4-32",
            },
        }
    )


def propose_design_config(
    *,
    scenario: dict[str, Any],
    exemplars: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
    retries: int = 2,
    temperature: float = 0.4,
) -> DesignConfig | None:
    """Ask Fireworks for a validated DesignConfig; ``None`` when unavailable.

    Returns ``None`` (never raises, never fakes) when the API key is missing,
    the ``openai`` SDK is absent, or all attempts fail to yield a config that
    passes ``validate_design``. Makes one real call per attempt (up to
    ``1 + retries``) using OpenAI-compatible JSON mode against Fireworks.
    """
    api_key = get_key("FIREWORKS_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=api_key, base_url=FIREWORKS_BASE)
    user_prompt = _build_user_prompt(scenario, exemplars)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    attempts = max(1, 1 + retries)
    for attempt in range(attempts):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
        except Exception:
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
                continue
            return None

        text = (completion.choices[0].message.content or "") if completion.choices else ""
        payload = _extract_json_object(text)
        design = _coerce_to_legal(payload) if payload else None
        if design is not None:
            return design
        # Bad/unparseable/invalid payload — nudge harder and retry.
        if attempt + 1 < attempts:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "That was not a valid JSON object with the required integer "
                        "keys in range. Return ONLY the JSON object."
                    ),
                }
            )
    return None
