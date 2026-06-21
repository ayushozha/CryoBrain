"""Exa literature RAG for decoder priors (SPEC2 F7.1, SPEC-v5 C6).

Real Exa search seeds memory with cited RTL/papers context for proposals.
The sponsor call is REAL when ``EXA_API_KEY`` is present and the official
``exa-py`` SDK is installed; it returns an empty list (clean skip) when either
is missing. Results are never fabricated in any production path.
"""

from __future__ import annotations

import time
from typing import Any

from cryobrain.integrations.secrets import get_key

DEFAULT_QUERY = (
    "neural quantum error correction decoder surface code "
    "real-time hardware cryogenic FPGA ASIC"
)

SNIPPET_CHARS = 500
DEFAULT_RETRIES = 2


def _client() -> Any | None:
    """Build a real Exa client, or ``None`` when key/SDK are unavailable."""
    api_key = get_key("EXA_API_KEY")
    if not api_key:
        return None
    try:
        from exa_py import Exa
    except ImportError:
        return None
    try:
        return Exa(api_key=api_key)
    except Exception:
        return None


def _snippet(item: Any) -> str:
    """Best available text snippet for a result (highlights, then full text)."""
    highlights = getattr(item, "highlights", None) or []
    if highlights:
        return " ".join(str(h) for h in highlights).strip()[:SNIPPET_CHARS]
    return (getattr(item, "text", "") or "").strip()[:SNIPPET_CHARS]


def _search_with_contents(exa: Any, query: str, num_results: int) -> Any:
    """Call Exa for results WITH contents so snippets actually populate.

    ``exa.search`` alone returns no text; ``search_and_contents`` is the
    documented way to get ``text``/``highlights``. Fall back to plain search
    only if the contents method is unavailable in an older SDK.
    """
    method = getattr(exa, "search_and_contents", None)
    if callable(method):
        return method(
            query,
            num_results=num_results,
            text={"max_characters": SNIPPET_CHARS},
            highlights=True,
        )
    return exa.search(query, num_results=num_results)


def search_decoder_literature(
    query: str = DEFAULT_QUERY,
    *,
    num_results: int = 5,
    retries: int = DEFAULT_RETRIES,
) -> list[dict[str, Any]]:
    """Return structured Exa hits; empty list when SDK/key unavailable.

    Each hit: ``{title, url, snippet, published_date}``. Retries transient
    failures with linear backoff; never raises into the caller.
    """
    exa = _client()
    if exa is None:
        return []

    response: Any = None
    for attempt in range(max(1, retries)):
        try:
            response = _search_with_contents(exa, query, num_results)
            break
        except Exception:
            if attempt + 1 >= max(1, retries):
                return []
            time.sleep(0.5 * (attempt + 1))

    hits: list[dict[str, Any]] = []
    for item in getattr(response, "results", []) or []:
        url = getattr(item, "url", "") or ""
        if not url:
            continue
        hits.append(
            {
                "title": getattr(item, "title", "") or "",
                "url": url,
                "snippet": _snippet(item),
                "published_date": getattr(item, "published_date", None),
            }
        )
    return hits


def fetch_decoder_context(
    query: str = DEFAULT_QUERY,
    *,
    num_results: int = 5,
) -> list[dict[str, str]]:
    """Cited decoder context for proposal/memory seeding (SPEC-v5 C6).

    Returns ``[{"url": ..., "snippet": ...}]`` — the documented C6 shape.
    Real Exa call when the key is present; empty list (clean skip) otherwise.
    URLs are retained so downstream memory records carry provenance.
    """
    return [
        {"url": hit["url"], "snippet": hit["snippet"]}
        for hit in search_decoder_literature(query, num_results=num_results)
        if hit.get("url")
    ]


def seed_memory_tags(hits: list[dict[str, Any]]) -> list[str]:
    """Compact citation tags for memory records."""
    tags: list[str] = []
    for hit in hits[:3]:
        title = str(hit.get("title", "")).strip()
        if title:
            tags.append(f"exa:{title[:80]}")
    return tags