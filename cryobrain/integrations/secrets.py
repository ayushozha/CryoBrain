"""Load sponsor API keys from environment / .env."""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    if env_path.is_file():
        # override=True so the project .env wins over stale placeholder values
        # left in the shell environment (e.g. an EXA_API_KEY=REPLACE_ME export
        # shadowing the real key). python-dotenv does NOT override existing env
        # vars by default, which silently 401s sponsor calls.
        load_dotenv(env_path, override=True)


def get_key(name: str) -> str | None:
    _load_dotenv()
    value = os.environ.get(name, "").strip()
    return value or None