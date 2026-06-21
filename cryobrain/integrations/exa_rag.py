"""Exa literature RAG for decoder priors (SPEC2 F7.1)."""

from __future__ import annotations

from typing import Any

from cryobrain.integrations.secrets import get_key

DEFAULT_QUERY = (
    "neural quantum error correction decoder surface code "
    "real-time hardware cryogenic FPGA ASIC"
)


def search_decoder_literature(
    query: str = DEFAULT_QUERY,
    *,
    num_results: int = 5,
) -> list[dict[str, Any]]:
    """Return Exa search hits; empty list when SDK/key unavailable."""
    api_key = get_key("EXA_API_KEY")
    if not api_key:
        return []
    try:
        from exa_py import Exa
    except ImportError:
        return []

    try:
        exa = Exa(api_key=api_key)
        response = exa.search(query, num_results=num_results)
    except Exception:
        return []
    hits: list[dict[str, Any]] = []
    for item in getattr(response, "results", []) or []:
        hits.append(
            {
                "title": getattr(item, "title", "") or "",
                "url": getattr(item, "url", "") or "",
                "snippet": (getattr(item, "text", "") or "")[:500],
                "published_date": getattr(item, "published_date", None),
            }
        )
    return hits


def seed_memory_tags(hits: list[dict[str, Any]]) -> list[str]:
    """Compact citation tags for memory records."""
    tags: list[str] = []
    for hit in hits[:3]:
        title = str(hit.get("title", "")).strip()
        if title:
            tags.append(f"exa:{title[:80]}")
    return tags