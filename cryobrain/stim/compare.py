"""Compare Stim-derived expected corrections against decoder outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CompareResult:
    total: int
    mismatches: int

    @property
    def matches(self) -> int:
        return self.total - self.mismatches

    @property
    def exactness(self) -> float:
        return self.matches / self.total if self.total else 0.0


def compare_corrections(expected: Iterable[int], observed: Iterable[int]) -> CompareResult:
    """Return deterministic mismatch counts for equal-length correction streams."""
    expected_list = list(expected)
    observed_list = list(observed)
    if len(expected_list) != len(observed_list):
        raise ValueError(f"expected {len(expected_list)} corrections, got {len(observed_list)}")
    mismatches = sum(1 for exp, obs in zip(expected_list, observed_list, strict=True) if int(exp) != int(obs))
    return CompareResult(total=len(expected_list), mismatches=mismatches)


def read_expected_corrections(vector_path: Path) -> list[int]:
    """Read the expected correction column from a two-column Stim vector file."""
    expected: list[int] = []
    for line_no, raw in enumerate(vector_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"{vector_path}:{line_no}: expected '<syndrome> <correction>'")
        expected.append(int(parts[1], 16))
    return expected


def compare_vector_file(vector_path: Path, observed: Iterable[int]) -> CompareResult:
    """Compare decoder outputs against expected corrections in ``vector_path``."""
    return compare_corrections(read_expected_corrections(vector_path), observed)
