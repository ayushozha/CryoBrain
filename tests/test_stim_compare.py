from pathlib import Path

import pytest

from cryobrain.stim.compare import compare_corrections, compare_vector_file, read_expected_corrections


def test_compare_corrections_counts_mismatches():
    result = compare_corrections([0x1, 0x2, 0x3, 0x4], [0x1, 0x0, 0x3, 0x5])
    assert result.total == 4
    assert result.matches == 2
    assert result.mismatches == 2
    assert result.exactness == 0.5


def test_compare_corrections_rejects_length_mismatch():
    with pytest.raises(ValueError, match="expected 2 corrections, got 1"):
        compare_corrections([0x1, 0x2], [0x1])


def test_compare_vector_file_reads_expected_column(tmp_path):
    vectors = tmp_path / "vectors.mem"
    vectors.write_text("# syndrome expected\n0a 03\nff 0c\n", encoding="utf-8")
    assert read_expected_corrections(vectors) == [0x3, 0xC]
    assert compare_vector_file(vectors, [0x3, 0x0]).mismatches == 1


def test_compare_vector_file_rejects_malformed_row(tmp_path):
    vectors = Path(tmp_path / "bad.mem")
    vectors.write_text("0a 03 extra\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected '<syndrome> <correction>'"):
        read_expected_corrections(vectors)
