"""Robustness measurements on a fixed fixture. They document measured behaviour, not universal guarantees."""

import numpy as np
import pytest

from analysis.watermarking import dct_watermark as dw, lsb_watermark as lw
from analysis.watermarking.attacks import ATTACKS, apply_attack
from analysis.watermarking.robustness import run_attack, run_suite

MSG, KEY = "VERIDIA-2026", "k"


@pytest.fixture
def dct_marked(natural):
    return dw.embed(natural, MSG, KEY)


@pytest.fixture
def lsb_marked(natural):
    return lw.embed(natural, MSG, KEY)


def test_attacks_preserve_shape_and_validate(natural):
    for attack in ATTACKS.values():
        assert apply_attack(natural, attack.name, attack.presets[0]).shape == natural.shape
    with pytest.raises(ValueError):
        apply_attack(natural, "jpeg", 0)
    with pytest.raises(ValueError):
        apply_attack(natural, "shear", 5)  # not in the catalogue
    with pytest.raises(ValueError):
        apply_attack(natural, "rotate", 999)  # out of the documented range


def test_jpeg(dct_marked, lsb_marked):
    _, dct_row = run_attack(dct_marked, "jpeg", 75, "dct", MSG, KEY)
    _, lsb_row = run_attack(lsb_marked, "jpeg", 75, "spatial_lsb", MSG, KEY)
    assert dct_row["status"] == "verified"
    assert lsb_row["status"] == "not_found" and lsb_row["bit_error_rate"] > 0.4  # LSBs are effectively randomised
    _, heavy = run_attack(dct_marked, "jpeg", 30, "dct", MSG, KEY)
    assert heavy["bit_error_rate"] > dct_row["bit_error_rate"]


def test_resize(dct_marked):
    _, row = run_attack(dct_marked, "rescale", 0.75, "dct", MSG, KEY)
    assert row["status"] == "verified" and row["psnr_db"] < 50


def test_noise(dct_marked, lsb_marked):
    assert run_attack(dct_marked, "noise", 5, "dct", MSG, KEY)[1]["status"] == "verified"
    assert run_attack(lsb_marked, "noise", 5, "spatial_lsb", MSG, KEY)[1]["status"] == "not_found"
    a, _ = run_attack(dct_marked, "noise", 5, "dct", MSG, KEY)
    b, _ = run_attack(dct_marked, "noise", 5, "dct", MSG, KEY)
    assert np.array_equal(a, b)  # seeded, reproducible


def test_suite_shape(dct_marked):
    rows = run_suite(dct_marked, "dct", MSG, KEY)
    assert len(rows) == 1 + sum(len(a.presets) for a in ATTACKS.values())
    assert rows[0]["attack"] == "none" and rows[0]["status"] == "verified" and rows[0]["psnr_db"] is None
