"""X1 guard: production paths must not contain the removed LER proxy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROD_ROOTS = ("cryobrain", "tasks", "scripts")
FORBIDDEN = ("simulate_candidate_ler", "decoder_quality_multiplier")
SKIP_SUFFIXES = {".gif", ".jpg", ".jpeg", ".pdf", ".png", ".pyc"}


def test_proxy_symbols_removed_from_production_paths():
    offenders: list[str] = []
    for root_name in PROD_ROOTS:
        for path in (ROOT / root_name).rglob("*"):
            if path.is_dir() or path.suffix.lower() in SKIP_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for forbidden in FORBIDDEN:
                if forbidden in text:
                    offenders.append(f"{path.relative_to(ROOT)}: {forbidden}")

    assert offenders == []
