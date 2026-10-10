"""One-level Haar transform and the DWT-domain watermark."""

import numpy as np
import pytest

from analysis.metrics import psnr
from analysis.watermarking import dwt_watermark as dw
from analysis.watermarking.common import WatermarkError
from analysis.watermarking.haar import haar2, ihaar2, subband_preview
from tests.conftest import natural_image

MSG, KEY = "VERIDIA-2026", "k"


# ---- transform ------------------------------------------------------------------------------------

@pytest.mark.parametrize("shape", [(2, 2), (8, 8), (64, 96), (128, 128)])
def test_haar_reconstructs_exactly(shape):
    x = np.random.default_rng(0).uniform(0, 255, shape)
    ll, lh, hl, hh = haar2(x)
    assert ll.shape == (shape[0] // 2, shape[1] // 2)
    assert np.abs(ihaar2(ll, lh, hl, hh) - x).max() < 1e-9


def test_haar_is_orthonormal_and_separates_detail():
    x = np.random.default_rng(1).uniform(-100, 100, (32, 32))
    bands = haar2(x)
    assert (x**2).sum() == pytest.approx(sum((b**2).sum() for b in bands))  # energy preserved
    _, lh, hl, hh = haar2(np.full((16, 16), 7.0))
    assert all(np.allclose(b, 0) for b in (lh, hl, hh))  # a flat image has no detail


def test_haar_rejects_odd_dimensions_and_mismatched_bands():
    with pytest.raises(ValueError, match="even"):
        haar2(np.zeros((5, 4)))
    with pytest.raises(ValueError, match="even"):
        haar2(np.zeros((4, 5)))
    with pytest.raises(ValueError, match="1-D|2-D"):
        haar2(np.zeros(8))
    with pytest.raises(ValueError, match="shape"):
        ihaar2(np.zeros((4, 4)), np.zeros((4, 4)), np.zeros((4, 4)), np.zeros((2, 2)))


def test_subband_preview_is_a_full_size_grayscale_tile(natural):
    preview = subband_preview(natural)
    assert preview.shape == natural.shape[:2] and preview.dtype == np.uint8


# ---- embedding and verification -------------------------------------------------------------------

def test_round_trip_deterministic_and_imperceptible(natural):
    marked = dw.embed(natural, MSG, KEY)
    assert np.array_equal(marked, dw.embed(natural, MSG, KEY))  # deterministic
    result = dw.verify(marked, KEY, MSG)
    assert (result.status, result.message) == ("verified", MSG)
    assert dw.bit_error_rate(marked, MSG, KEY) == 0.0
    assert psnr(natural, marked) > 35  # measured ~38 dB at the default strength


def test_input_is_not_modified(natural):
    before = natural.copy()
    dw.embed(natural, MSG, KEY)
    assert np.array_equal(natural, before)


def test_extract_mismatch_wrong_key_and_unmarked(natural):
    marked = dw.embed(natural, "owner:alice", KEY)
    assert dw.verify(marked, KEY).status == "extracted"
    assert dw.verify(marked, KEY, "owner:bob").status == "mismatch"
    assert dw.verify(marked, "wrong-key").status == "not_found"
    assert dw.verify(natural, KEY).status == "not_found"


def test_invalid_input_rejected(natural):
    with pytest.raises(WatermarkError):
        dw.embed(natural, "")
    with pytest.raises(WatermarkError):
        dw.embed(natural, "x" * (dw.MAX_MESSAGE_BYTES + 1))
    with pytest.raises(WatermarkError, match="Strength"):
        dw.embed(natural, "ok", strength=0)
    with pytest.raises(WatermarkError, match="too small"):
        dw.embed(natural[:32, :32], "ok")
    assert dw.verify(natural[:32, :32]).status == "not_found"


def test_capacity_and_parameters(natural):
    assert dw.capacity_carriers(natural) == (natural.shape[0] // 2) * (natural.shape[1] // 2)
    params = dw.parameters(natural, 8.0)
    assert params["payload_bits"] == dw.PAYLOAD_BITS and params["strength"] == 8.0
    assert params["copies"] == pytest.approx(dw.capacity_carriers(natural) / dw.PAYLOAD_BITS, abs=0.01)
    # the smallest image that still carries the required redundancy
    smallest = natural_image(48, 48)
    assert dw.capacity_carriers(smallest) >= dw.PAYLOAD_BITS * dw.MIN_COPIES
    assert dw.verify(dw.embed(smallest, "s", KEY), KEY, "s").status == "verified"


def test_odd_dimensions_leave_the_remainder_untouched():
    img = natural_image(201, 251)
    marked = dw.embed(img, "hi", KEY)
    assert marked.shape == img.shape
    assert np.array_equal(marked[200:], img[200:]) and np.array_equal(marked[:, 250:], img[:, 250:])
    assert dw.verify(marked, KEY, "hi").status == "verified"


def test_changes_stay_in_luminance_detail_not_the_whole_image(natural):
    """A sanity check that the mark is a small perturbation, not a rewrite."""
    marked = dw.embed(natural, MSG, KEY)
    delta = np.abs(marked.astype(int) - natural.astype(int))
    assert delta.max() <= 40  # bounded local change
    assert delta.mean() < 5  # and small on average
