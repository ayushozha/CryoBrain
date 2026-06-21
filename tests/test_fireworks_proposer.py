"""C2: Fireworks proposer -> validated DesignConfig.

Offline tests run always (import, no-key contract, parse/coerce/validation).
The live test makes ONE real Fireworks call and is skipped without the key.
No mocked responses live in production code paths; the monkeypatched client
here exists only to exercise the *validation* boundary, never to ship.
"""

from __future__ import annotations

import pytest

from cryobrain.design.validators import validate_design
from cryobrain.integrations import fireworks
from cryobrain.integrations.secrets import get_key
from cryobrain.rl import proposer
from cryobrain.types import DesignConfig

HAS_KEY = bool(get_key("FIREWORKS_API_KEY"))


# --- offline: import + JSON extraction / coercion / validation ----------------


def test_imports():
    assert callable(proposer.propose_next_design)
    assert callable(fireworks.propose_design_config)


def test_extract_json_handles_prose_and_fences():
    assert fireworks._extract_json_object('{"bitwidth": 4}') == {"bitwidth": 4}
    assert fireworks._extract_json_object('here you go: {"bitwidth": 8} done') == {"bitwidth": 8}
    fenced = "```json\n{\"num_layers\": 2}\n```"
    assert fireworks._extract_json_object(fenced) == {"num_layers": 2}
    # Nested braces must not break extraction (the old [^{}] regex did).
    nested = '{"a": {"b": 1}, "bitwidth": 2}'
    assert fireworks._extract_json_object(nested) == {"a": {"b": 1}, "bitwidth": 2}


def test_extract_json_rejects_garbage():
    assert fireworks._extract_json_object("not json at all") is None
    assert fireworks._extract_json_object("") is None
    assert fireworks._extract_json_object("[1, 2, 3]") is None  # array, not object


def test_coerce_snaps_and_clamps_into_legal_space():
    # Out-of-range / non-allowed values must be coerced into a *valid* config.
    design = fireworks._coerce_to_legal(
        {
            "bitwidth": 5,        # -> nearest of {2,4,8} = 4
            "parallelism": 3,     # -> nearest of {1,2,4} = 2 or 4
            "num_layers": 99,     # -> clamp to 8
            "pipeline_depth": 0,  # -> clamp to 1
            "window_length": 2,   # -> clamp to 4
        }
    )
    assert design is not None
    validate_design(design)  # must not raise
    assert design.bitwidth == 4
    assert design.parallelism in (2, 4)
    assert design.num_layers == 8
    assert design.pipeline_depth == 1
    assert design.window_length == 4


def test_coerce_rejects_non_numeric():
    assert fireworks._coerce_to_legal({"bitwidth": "wide"}) is None


# --- offline: no-key contract -------------------------------------------------


def test_propose_next_design_raises_without_key(monkeypatch):
    monkeypatch.setattr(proposer, "get_key", lambda _name: None)
    with pytest.raises(RuntimeError, match="FIREWORKS_API_KEY"):
        proposer.propose_next_design({"scenario": {"distance": 3}})


def test_propose_next_design_soft_returns_none_without_key(monkeypatch):
    monkeypatch.setattr(proposer, "get_key", lambda _name: None)
    assert proposer.propose_next_design({}, strict=False) is None


def test_low_level_proposer_returns_none_without_key(monkeypatch):
    monkeypatch.setattr(fireworks, "get_key", lambda _name: None)
    assert fireworks.propose_design_config(scenario={}, exemplars=[]) is None


# --- offline: malformed live response is rejected (validation boundary) -------


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        return _FakeCompletion(self._content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeOpenAI:
    """Test-only stand-in for openai.OpenAI returning a canned payload."""

    last = None

    def __init__(self, *_a, **_k):
        self.chat = _FakeChat(type(self)._content)
        type(self).last = self


def _patch_client(monkeypatch, content):
    monkeypatch.setattr(fireworks, "get_key", lambda _name: "test-key")
    import openai

    fake = type("FakeOpenAI", (_FakeOpenAI,), {"_content": content})
    monkeypatch.setattr(openai, "OpenAI", fake)
    return fake


def test_malformed_response_is_rejected(monkeypatch):
    # Model returns prose with no JSON object -> proposer must return None,
    # never a fabricated config. Retries are exhausted, so >1 call happens.
    fake = _patch_client(monkeypatch, "I cannot help with that.")
    result = fireworks.propose_design_config(scenario={}, exemplars=[], retries=1)
    assert result is None
    assert fake.last.chat.completions.calls == 2  # 1 + 1 retry


def test_valid_response_is_accepted(monkeypatch):
    _patch_client(
        monkeypatch,
        '{"bitwidth": 8, "num_layers": 3, "parallelism": 2, '
        '"pipeline_depth": 6, "window_length": 16}',
    )
    result = fireworks.propose_design_config(scenario={}, exemplars=[])
    assert isinstance(result, DesignConfig)
    validate_design(result)
    assert result.bitwidth == 8 and result.window_length == 16


def test_out_of_bounds_response_is_coerced_not_trusted(monkeypatch):
    # A nominally-parseable but out-of-spec payload must be snapped into the
    # legal space (never trusted raw) and still validate.
    _patch_client(
        monkeypatch,
        '{"bitwidth": 3, "num_layers": 50, "parallelism": 7, '
        '"pipeline_depth": 99, "window_length": 1}',
    )
    result = fireworks.propose_design_config(scenario={}, exemplars=[])
    assert isinstance(result, DesignConfig)
    validate_design(result)  # the load-bearing assertion: output is always legal


# --- live: one real Fireworks call (skipped without key) ----------------------


@pytest.mark.skipif(not HAS_KEY, reason="FIREWORKS_API_KEY not set")
def test_live_propose_next_design_returns_valid_config():
    snapshot = {
        "scenario": {"distance": 3, "noise_rate": 0.001},
        "best": [
            {
                "design": DesignConfig().to_dict(),
                "reward": 0.1,
                "metrics": {"candidate_ler": 0.02, "suppression": 0.1},
            }
        ],
    }
    design = proposer.propose_next_design(snapshot)
    assert isinstance(design, DesignConfig)
    validate_design(design)  # real model output, validated
