import numpy as np
import pytest

from analysis.watermarking import lsb_watermark as wm


def test_round_trip_and_determinism(pixels):
    marked = wm.embed(pixels, "owner:alice", key="k1")
    assert np.array_equal(marked, wm.embed(pixels, "owner:alice", key="k1"))
    assert np.max(np.abs(marked.astype(int) - pixels.astype(int))) <= 1
    result = wm.verify(marked, key="k1", expected="owner:alice")
    assert (result.status, result.message, result.bit_agreement) == ("verified", "owner:alice", 1.0)


def test_extract_without_expected(pixels):
    assert wm.verify(wm.embed(pixels, "abc"), expected=None).status == "extracted"


def test_mismatch_wrong_key_and_unmarked(pixels):
    marked = wm.embed(pixels, "owner:alice", key="k1")
    assert wm.verify(marked, "k1", "owner:bob").status == "mismatch"
    assert wm.verify(marked, "wrong-key").status == "not_found"
    assert wm.verify(pixels, "k1").status == "not_found"


def test_tolerates_sparse_bit_damage(pixels):
    marked = wm.embed(pixels, "owner:alice", key="k1")
    damaged = marked.reshape(-1).copy()
    damaged[::97] ^= 1  # flip ~1% of LSBs
    assert wm.verify(damaged.reshape(marked.shape), "k1", "owner:alice").status == "verified"


def test_rejects_invalid_input(pixels):
    with pytest.raises(wm.WatermarkError):
        wm.embed(pixels, "")
    with pytest.raises(wm.WatermarkError):
        wm.embed(pixels, "x" * 65)
    with pytest.raises(wm.WatermarkError):
        wm.embed(pixels[:8, :8], "tiny")
