"""Assemble Exa hits into a context pack carrying citation provenance.

The pack is what a proposer model is prompted with and what later memory
records cite. Provenance (the source URLs) is stored explicitly so a verified
design can be traced back to the literature that seeded it (SPEC-v5 C6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cryobrain.integrations.exa_rag import DEFAULT_QUERY, fetch_decoder_context


@dataclass
class ContextPack:
    """Retrieved literature context for a proposal, with provenance."""

    query: str
    hits: list[dict[str, str]] = field(default_factory=list)

    @property
    def urls(self) -> list[str]:
        """Provenance URLs, in retrieval order (deduped, non-empty)."""
        seen: set[str] = set()
        ordered: list[str] = []
        for hit in self.hits:
            url = hit.get("url", "")
            if url and url not in seen:
                seen.add(url)
                ordered.append(url)
        return ordered

    def prompt_block(self) -> str:
        """Cited context block to splice into a proposer prompt."""
        lines = [f"[{i}] {h['url']}\n{h['snippet']}" for i, h in enumerate(self.hits, 1)]
        return "\n\n".join(lines)

    def memory_tags(self) -> list[str]:
        """Compact provenance tags for a memory record."""
        return [f"exa:{url}" for url in self.urls]

    def to_dict(self) -> dict[str, Any]:
        return {"query": self.query, "hits": list(self.hits), "urls": self.urls}


def build_context_pack(
    query: str = DEFAULT_QUERY,
    *,
    num_results: int = 5,
) -> ContextPack:
    """Fetch decoder context from Exa and wrap it as a ContextPack.

    Empty hits when the Exa key/SDK is absent — the pack is still valid and
    carries an empty provenance list (no fabricated citations).
    """
    hits = fetch_decoder_context(query, num_results=num_results)
    return ContextPack(query=query, hits=hits)
