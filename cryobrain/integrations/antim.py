"""Antim Gizmo concept visual hook (SPEC2 optional sponsor)."""

from __future__ import annotations

from typing import Any

import json
import urllib.error
import urllib.request

from cryobrain.integrations.secrets import get_key

GIZMO_BASE = "https://gizmo.antimlabs.com/api/v1"


def request_concept_visual(
    prompt: str,
    *,
    style: str = "technical-diagram",
) -> dict[str, Any]:
    """Request a concept visual from Antim Gizmo; best-effort."""
    api_key = get_key("ANTIM_GIZMO_API_KEY")
    if not api_key:
        return {"ok": False, "error": "ANTIM_GIZMO_API_KEY unset"}

    body = json.dumps({"prompt": prompt, "style": style}).encode("utf-8")
    req = urllib.request.Request(
        f"{GIZMO_BASE}/generate",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return {"ok": True, "payload": payload, "backend": "antim-gizmo"}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}", "backend": "antim-gizmo"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "backend": "antim-gizmo"}