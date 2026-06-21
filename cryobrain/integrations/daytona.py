"""Daytona sandbox integration (SPEC-v5 sponsor: Daytona).

Provides a key-guarded, import-guarded lifecycle for forking an isolated Linux
workdir per measurement variant: create -> run -> destroy. The official Daytona
Python SDK (``daytona`` / ``daytona-sdk``) is preferred over hand-rolled HTTP;
it pulls native wheels and is typically only installed on Linux/WSL, so every
entry point here degrades cleanly when the SDK or key is absent.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from cryobrain.integrations.secrets import get_key


def daytona_available() -> bool:
    """True when the Daytona SDK is importable and an API key is configured."""
    if not get_key("DAYTONA_API_KEY"):
        return False
    try:
        import daytona  # noqa: F401
    except ImportError:
        return False
    return True


def _client() -> Any:
    """Construct an authenticated Daytona client. Caller must guard imports."""
    from daytona import Daytona, DaytonaConfig

    api_key = get_key("DAYTONA_API_KEY")
    if not api_key:
        raise RuntimeError("DAYTONA_API_KEY unset")
    return Daytona(DaytonaConfig(api_key=api_key))


@contextmanager
def daytona_sandbox(**create_kwargs: Any) -> Iterator[Any]:
    """Yield a freshly created Daytona sandbox; always delete it on exit.

    The sandbox is destroyed in a ``finally`` block even if the caller raises,
    so a failed measurement never leaks a running sandbox. Never yields a fake
    sandbox: raises ``RuntimeError`` if the SDK or key is missing.
    """
    if not daytona_available():
        raise RuntimeError("Daytona SDK or DAYTONA_API_KEY unavailable")
    daytona = _client()
    sandbox = daytona.create(**create_kwargs) if create_kwargs else daytona.create()
    try:
        yield sandbox
    finally:
        try:
            sandbox.delete()
        except Exception:
            # Best-effort teardown; a delete failure must not mask the real error.
            pass


def run_python_sandbox(code: str, *, timeout_sec: int = 30) -> dict[str, Any]:
    """Execute Python in a Daytona sandbox; degrade cleanly when unavailable."""
    if not get_key("DAYTONA_API_KEY"):
        return {"ok": False, "error": "DAYTONA_API_KEY unset", "backend": "none"}
    try:
        import daytona  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "daytona package not installed", "backend": "none"}

    try:
        with daytona_sandbox() as sandbox:
            response = sandbox.process.code_run(code, timeout=timeout_sec)
            return {
                "ok": int(getattr(response, "exit_code", 1)) == 0,
                "exit_code": getattr(response, "exit_code", None),
                "result": getattr(response, "result", ""),
                "backend": "daytona",
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "backend": "daytona"}
