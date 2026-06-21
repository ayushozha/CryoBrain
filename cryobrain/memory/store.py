"""Measured-variant memory store (SPEC-v5 C1).

Persists one :class:`~cryobrain.memory.models.MemoryRecord` per measured,
verified decoder variant, keyed by a stable ``rtl_hash`` (sha256 of the RTL
file contents) for dedupe and provenance.

Backend: a JSONL file (one record per line) — the simplest reliable store for
the hackathon. No DB dependency (minimal-code-dependency-first); ``schema.sql``
is intentionally absent. This sits BESIDE the reward-ranked
:class:`~cryobrain.memory.buffer.VerifiedDesignBuffer` (SPEC2/WS5), which is
consumed elsewhere and left untouched.

Public API (per HANDOFF-CLAUDE.md C1):
  * ``record_variant(record) -> rtl_hash``  — C5 writes measured variants.
  * ``best_holdout() -> MemoryRecord | None`` — best by measured candidate_ler.
  * ``query_pareto_candidates() -> list[ParetoCandidate]`` — C10 reads these.

The holdout / pareto LER always comes from ``measurement.candidate_ler``, which
is sourced from ``measure_candidate_ler`` (MeasureResult) — never a proxy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cryobrain.memory.models import MemoryRecord

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORE = ROOT / "artifacts" / "measured_variants.jsonl"


def rtl_hash(rtl_path: Path | str) -> str:
    """Stable sha256 of the RTL file contents (stdlib only)."""
    data = Path(rtl_path).read_bytes()
    return hashlib.sha256(data).hexdigest()


class ParetoCandidate(dict):
    """Plain dict carrying the fields C10's pareto needs.

    Keys: ``rtl_hash``, ``rtl_path``, ``ler`` (measured candidate_ler),
    ``area_um2``, ``latency_cycles``.
    """


class MemoryStore:
    """JSONL-backed store of measured variants, keyed by ``rtl_hash``."""

    def __init__(self, path: Path | str = DEFAULT_STORE) -> None:
        self.path = Path(path)
        # rtl_hash -> MemoryRecord; dict preserves insertion order for stable reads.
        self._records: dict[str, MemoryRecord] = {}
        if self.path.is_file():
            self._load()

    # -- persistence -------------------------------------------------------
    def _load(self) -> None:
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            key = str(raw.pop("rtl_hash"))
            self._records[key] = MemoryRecord.model_validate(raw)

    def _append(self, key: str, record: MemoryRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"rtl_hash": key, **record.model_dump()}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

    def _rewrite(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps({"rtl_hash": key, **rec.model_dump()})
            for key, rec in self._records.items()
        ]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # -- public API --------------------------------------------------------
    def record_variant(self, record: MemoryRecord | dict[str, Any]) -> str:
        """Persist one measured variant; return its ``rtl_hash``.

        ``record`` may be a :class:`MemoryRecord` or a raw dict (validated here).
        The key is sha256 of the RTL file at ``record.rtl_path``; if the file is
        unavailable we fall back to hashing the recorded path string so the store
        still round-trips in fixture-only tests. Re-recording the same hash
        overwrites (dedupe) and rewrites the file.
        """
        rec = record if isinstance(record, MemoryRecord) else MemoryRecord.model_validate(record)
        try:
            key = rtl_hash(rec.rtl_path)
        except (FileNotFoundError, OSError):
            key = hashlib.sha256(rec.rtl_path.encode("utf-8")).hexdigest()

        seen = key in self._records
        self._records[key] = rec
        if seen:
            self._rewrite()
        else:
            self._append(key, rec)
        return key

    def all_records(self) -> list[MemoryRecord]:
        return list(self._records.values())

    def best_holdout(self) -> MemoryRecord | None:
        """Best verified variant by measured ``candidate_ler`` (lowest wins).

        Only verification-passed records are eligible. LER is the measured
        ``candidate_ler`` (from ``measure_candidate_ler``), never a proxy.
        """
        verified = [r for r in self._records.values() if r.verification.passed]
        if not verified:
            return None
        return min(verified, key=lambda r: r.measurement.candidate_ler)

    def query_pareto_candidates(self) -> list[ParetoCandidate]:
        """Candidates carrying (ler, area_um2, latency_cycles, rtl_path) for C10.

        ``ler`` is the measured ``candidate_ler``. Only verified records are
        returned, sorted by ascending measured LER for a stable, sensible order.
        """
        out: list[ParetoCandidate] = []
        for key, rec in self._records.items():
            if not rec.verification.passed:
                continue
            out.append(
                ParetoCandidate(
                    rtl_hash=key,
                    rtl_path=rec.rtl_path,
                    ler=rec.measurement.candidate_ler,
                    area_um2=rec.synth.area_um2,
                    latency_cycles=rec.synth.latency_cycles,
                )
            )
        out.sort(key=lambda c: c["ler"])
        return out

    def __len__(self) -> int:
        return len(self._records)


# Module-level convenience over the default store path -----------------------
def record_variant(
    record: MemoryRecord | dict[str, Any], *, path: Path | str = DEFAULT_STORE
) -> str:
    return MemoryStore(path).record_variant(record)


def best_holdout(*, path: Path | str = DEFAULT_STORE) -> MemoryRecord | None:
    return MemoryStore(path).best_holdout()


def query_pareto_candidates(*, path: Path | str = DEFAULT_STORE) -> list[ParetoCandidate]:
    return MemoryStore(path).query_pareto_candidates()
