import numpy as np
import pytest

from analysis.steganography import keyed_lsb


def test_keyed_round_trip(pixels):
    stego = keyed_lsb.embed_text(pixels, "Hello Veridia!", "demo-key")
    assert keyed_lsb.extract_text(stego, "demo-key") == "Hello Veridia!"


def test_wrong_key_fails(pixels):
    stego = keyed_lsb.embed_text(pixels, "secret message", "correct-key")
    with pytest.raises(keyed_lsb.NoPayloadError):
        keyed_lsb.extract(stego, "wrong-key")


def test_input_is_not_modified(pixels):
    original = pixels.copy()
    keyed_lsb.embed_text(pixels, "secret", "my-key")
    assert np.array_equal(pixels, original)


def test_same_key_and_image_are_deterministic(pixels):
    first = keyed_lsb.embed_text(pixels, "secret", "my-key")
    second = keyed_lsb.embed_text(pixels, "secret", "my-key")
    assert np.array_equal(first, second)


def test_different_keys_produce_different_results(pixels):
    first = keyed_lsb.embed_text(pixels, "secret", "key-one")
    second = keyed_lsb.embed_text(pixels, "secret", "key-two")
    assert not np.array_equal(first, second)


def test_capacity_exceeded(pixels):
    capacity = keyed_lsb.capacity_bytes(pixels)
    with pytest.raises(keyed_lsb.CapacityError):
        keyed_lsb.embed(pixels, b"x" * (capacity + 1), "my-key")


def test_empty_payload_rejected(pixels):
    with pytest.raises(keyed_lsb.KeyedLsbError):
        keyed_lsb.embed(pixels, b"", "my-key")


def test_invalid_image_dtype_rejected():
    pixels = np.zeros((32, 32, 3), dtype=np.int32)
    with pytest.raises(keyed_lsb.KeyedLsbError):
        keyed_lsb.embed(pixels, b"secret", "my-key")
