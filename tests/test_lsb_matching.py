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


def test_saturated_pixels_change_by_at_most_one():
    """0 and 255 must move inwards; a wrap-around (255 -> 0) would still pass a 0..255 range check."""
    pixels = np.random.default_rng(1).choice(np.array([0, 1, 254, 255], dtype=np.uint8), size=(64, 64, 3))
    payload = np.random.default_rng(2).integers(0, 256, pixels.size // 8, dtype=np.uint8).tobytes()  # full capacity
    stego = lsb_matching.embed(pixels, payload, seed=7)
    assert np.abs(stego.astype(int) - pixels.astype(int)).max() <= 1
    assert lsb_matching.extract(stego, len(payload), seed=7) == payload


def test_embedding_is_deterministic_and_seed_dependent(pixels):
    payload = b"repeatable"
    assert np.array_equal(lsb_matching.embed(pixels, payload, seed=9), lsb_matching.embed(pixels, payload, seed=9))
    assert not np.array_equal(lsb_matching.embed(pixels, payload, seed=9), lsb_matching.embed(pixels, payload, seed=10))


def test_only_the_keyed_samples_change_and_each_carries_its_bit(pixels):
    """Pins the RNG contract: the sample order is the first draw from a fresh generator.

    Drawing anything before the permutation would reorder the carriers and silently
    make previously embedded images unreadable, while a round-trip test still passed.
    """
    payload = np.random.default_rng(3).integers(0, 256, 200, dtype=np.uint8).tobytes()
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    order = np.random.default_rng(11).permutation(pixels.size)[: bits.size]

    stego = lsb_matching.embed(pixels, payload, seed=11)
    flat_in, flat_out = pixels.reshape(-1), stego.reshape(-1)

    assert np.array_equal(flat_out[order] & 1, bits)  # every carrier holds its bit
    untouched = np.setdiff1d(np.arange(pixels.size), order)
    assert np.array_equal(flat_out[untouched], flat_in[untouched])  # nothing else moved


def test_non_contiguous_input_is_supported_and_not_mutated(pixels):
    view = pixels[::2, ::2]
    assert not view.flags["C_CONTIGUOUS"]
    before = view.copy()
    stego = lsb_matching.embed(view, b"sliced", seed=4)
    assert np.array_equal(view, before)
    assert lsb_matching.extract(stego, 6, seed=4) == b"sliced"


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
