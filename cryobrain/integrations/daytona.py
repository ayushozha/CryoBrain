"""Daytona sandbox for isolated Python eval (SPEC2 sponsor)."""

from __future__ import annotations

from typing import Any

from cryobrain.integrations.secrets import get_key


def run_python_sandbox(code: str, *, timeout_sec: int = 30) -> dict[str, Any]:
    """Execute Python in a Daytona sandbox; falls back when SDK unavailable."""
    api_key = get_key("DAYTONA_API_KEY")
    if not api_key:
        return {"ok": False, "error": "DAYTONA_API_KEY unset", "backend": "none"}

    try:
        from daytona import Daytona, DaytonaConfig
    except ImportError:
        return {"ok": False, "error": "daytona package not installed", "backend": "none"}

    config = DaytonaConfig(api_key=api_key)
    daytona = Daytona(config)
    sandbox = daytona.create()
    try:
        response = sandbox.process.code_run(code, timeout=timeout_sec)
        ok = int(getattr(response, "exit_code", 1)) == 0
        return {
            "ok": ok,
            "exit_code": getattr(response, "exit_code", None),
            "result": getattr(response, "result", ""),
            "backend": "daytona",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "backend": "daytona"}
    finally:
        try:
            sandbox.delete()
        except Exception:
            pass