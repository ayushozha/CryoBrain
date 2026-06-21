"""G9: DesignConfig validation and mutation."""

from __future__ import annotations

import pytest

from cryobrain.design.config import mutate, preset_variants, sample_random
from cryobrain.design.validators import validate_design
from cryobrain.types import DesignConfig


def test_default_design_valid():
    validate_design(DesignConfig())


def test_preset_variants_distinct():
    variants = preset_variants()
    assert len(variants) == 3
    keys = [tuple(sorted(v.to_dict().items())) for v in variants]
    assert len(set(keys)) == 3


def test_invalid_bitwidth_rejected():
    with pytest.raises(ValueError, match="bitwidth"):
        validate_design(DesignConfig(bitwidth=16))


def test_mutate_and_sample_stay_valid():
    base = DesignConfig()
    validate_design(mutate(base))
    validate_design(sample_random())