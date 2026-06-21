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
        load_dotenv(env_path)


def get_key(name: str) -> str | None:
    _load_dotenv()
    value = os.environ.get(name, "").strip()
    return value or None