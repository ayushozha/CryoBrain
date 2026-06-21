"""C6 — Exa retrieval + context pack.

Offline tests (imports + schema + provenance) always run. A single live Exa
search runs ONLY when ``EXA_API_KEY`` is present AND the ``exa-py`` SDK is
importable; otherwise it is skipped cleanly. No Exa responses are faked.
"""

from __future__ import annotations

import importlib.util

import pytest

from cryobrain.integrations.exa_rag import (
    DEFAULT_QUERY,
    fetch_decoder_context,
    search_decoder_literature,
)
from cryobrain.integrations.secrets import get_key
from cryobrain.retrieval import ContextPack, build_context_pack

_HAS_KEY = get_key("EXA_API_KEY") is not None
_HAS_SDK = importlib.util.find_spec("exa_py") is not None
_LIVE = _HAS_KEY and _HAS_SDK
_LIVE_REASON = "needs EXA_API_KEY and exa-py SDK installed"


# ---------------------------------------------------------------- offline ---


def test_fetch_decoder_context_importable_and_returns_list():
    out = fetch_decoder_context(num_results=1)
    assert isinstance(out, list)
    for hit in out:
        assert set(hit) >= {"url", "snippet"}
        assert isinstance(hit["url"], str)
        assert isinstance(hit["snippet"], str)


def test_clean_skip_without_key(monkeypatch):
    """No key -> empty list, never an exception, never fabricated data."""
    monkeypatch.setattr(
        "cryobrain.integrations.exa_rag.get_key", lambda name: None
    )
    assert search_decoder_literature() == []
    assert fetch_decoder_context() == []
    pack = build_context_pack()
    assert isinstance(pack, ContextPack)
    assert pack.hits == []
    assert pack.urls == []


def test_context_pack_provenance_shape():
    pack = ContextPack(
        query="q",
        hits=[
            {"url": "https://a.example/p", "snippet": "alpha"},
            {"url": "https://b.example/p", "snippet": "beta"},
            {"url": "https://a.example/p", "snippet": "dup"},  # deduped
            {"url": "", "snippet": "no url dropped"},
        ],
    )
    assert pack.urls == ["https://a.example/p", "https://b.example/p"]
    assert pack.memory_tags() == [
        "exa:https://a.example/p",
        "exa:https://b.example/p",
    ]
    assert "https://a.example/p" in pack.prompt_block()
    assert pack.to_dict()["urls"] == pack.urls


# ------------------------------------------------------------------- live ---


def _key_is_usable() -> bool:
    """True only if the resolved EXA key actually authenticates.

    The ``_LIVE`` gate only proves a key *string* is present, but a stale
    placeholder (e.g. ``EXA_API_KEY=REPLACE_ME`` exported in the shell, which
    python-dotenv won't override unless the project .env is loaded) passes that
    gate yet 401s. A direct probe distinguishes "no usable key" (skip) from a
    real "valid key but Exa returned nothing" (fail loudly).
    """
    from cryobrain.integrations.exa_rag import _client

    client = _client()
    if client is None:
        return False
    try:
        client.search("quantum error correction", num_results=1)
        return True
    except Exception as exc:  # noqa: BLE001 - auth/transport -> not usable
        if "401" in str(exc) or "INVALID_API_KEY" in str(exc):
            return False
        raise


@pytest.mark.skipif(not _LIVE, reason=_LIVE_REASON)
def test_live_search_returns_cited_results():
    if not _key_is_usable():
        pytest.skip("EXA_API_KEY present but not usable (placeholder/invalid/401)")
    pack = build_context_pack(DEFAULT_QUERY, num_results=3)
    assert pack.hits, "live Exa search returned no results"
    first = pack.hits[0]
    assert first["url"].startswith("http")
    assert first["snippet"].strip()
    assert pack.urls, "provenance URLs must be populated from live hits"
