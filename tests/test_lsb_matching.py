import numpy as np
import pytest

from analysis.steganography import lsb_matching


@pytest.fixture
def pixels():
    rng = np.random.default_rng(42)
    return rng.integers(0, 256, size=(128, 128, 3), dtype=np.uint8)


def test_round_trip(pixels):
    payload = b"Veridia"
    stego = lsb_matching.embed(pixels, payload, seed=42)
    assert lsb_matching.extract(stego, len(payload), seed=42) == payload


def test_input_not_modified(pixels):
    original = pixels.copy()
    lsb_matching.embed(pixels, b"hello", seed=42)
    assert np.array_equal(pixels, original)


def test_pixel_values_remain_valid():
    pixels = np.zeros((32, 32), dtype=np.uint8)
    stego = lsb_matching.embed(pixels, b"\xff" * 32, seed=42)
    assert stego.min() >= 0
    assert stego.max() <= 255


def test_payload_too_large():
    pixels = np.zeros((2, 2), dtype=np.uint8)
    with pytest.raises(lsb_matching.LsbMatchingError):
        lsb_matching.embed(pixels, b"hello", seed=42)


def test_empty_payload_rejected(pixels):
    with pytest.raises(lsb_matching.LsbMatchingError):
        lsb_matching.embed(pixels, b"", seed=42)


def test_invalid_length_rejected(pixels):
    with pytest.raises(lsb_matching.LsbMatchingError):
        lsb_matching.extract(pixels, 0, seed=42)
