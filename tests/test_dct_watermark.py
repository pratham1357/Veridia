import numpy as np
import pytest

from analysis.metrics import psnr
from analysis.watermarking import dct_watermark as dw
from analysis.watermarking.common import WatermarkError
from analysis.watermarking.dct import block_dct, block_idct, dct_matrix, rgb_to_ycbcr, ycbcr_to_rgb
from tests.conftest import natural_image


def test_dct_primitives():
    d = dct_matrix()
    assert np.allclose(d @ d.T, np.eye(8))
    channel = np.random.default_rng(0).uniform(0, 255, (16, 24))
    assert np.allclose(block_idct(block_dct(channel)), channel)
    flat = np.full((8, 8), 10.0)
    coeffs = block_dct(flat)[0, 0]
    assert coeffs[0, 0] == pytest.approx(80.0) and np.allclose(coeffs.ravel()[1:], 0)  # constant block -> DC only


def test_colour_round_trip(natural):
    assert np.max(np.abs(ycbcr_to_rgb(rgb_to_ycbcr(natural)).astype(int) - natural)) <= 1


def test_round_trip_deterministic_and_imperceptible(natural):
    marked = dw.embed(natural, "VERIDIA-2026", key="k")
    assert np.array_equal(marked, dw.embed(natural, "VERIDIA-2026", key="k"))
    result = dw.verify(marked, key="k", expected="VERIDIA-2026")
    assert (result.status, result.message) == ("verified", "VERIDIA-2026")
    assert dw.bit_error_rate(marked, "VERIDIA-2026", "k") == 0.0
    assert psnr(natural, marked) > 38  # default strength, measured on this fixture


def test_extract_mismatch_wrong_key_unmarked(natural):
    marked = dw.embed(natural, "owner:alice", key="k")
    assert dw.verify(marked, "k").status == "extracted"
    assert dw.verify(marked, "k", "owner:bob").status == "mismatch"
    assert dw.verify(marked, "wrong").status == "not_found"
    assert dw.verify(natural, "k").status == "not_found"


def test_invalid_input(natural):
    with pytest.raises(WatermarkError):
        dw.embed(natural, "")
    with pytest.raises(WatermarkError):
        dw.embed(natural, "x" * 17)
    with pytest.raises(WatermarkError):
        dw.embed(natural, "ok", strength=0)
    with pytest.raises(WatermarkError, match="too small"):
        dw.embed(natural[:64, :64], "ok")
    assert dw.verify(natural[:64, :64]).status == "not_found"


def test_dimensions_not_multiple_of_eight():
    img = natural_image(203, 251)
    marked = dw.embed(img, "hi", key="k")
    assert dw.verify(marked, "k", "hi").status == "verified"
    assert np.array_equal(marked[200:], img[200:]) and np.array_equal(marked[:, 248:], img[:, 248:])
