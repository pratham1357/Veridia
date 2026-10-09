import numpy as np
import pytest

from analysis.steganography import spa


def test_analyze_returns_expected_fields():
    image = np.random.default_rng(42).integers(
        0, 256, size=(64, 64, 3), dtype=np.uint8
    )
    result = spa.analyze(image)

    assert result["method"] == "adjacent_pair_parity_screen"
    assert result["sample_count"] == image.size
    assert result["pair_count"] == image.size - 1
    assert 0.0 <= result["score"] <= 1.0


def test_counts_sum_to_total():
    image = np.arange(256, dtype=np.uint8)
    result = spa.analyze(image)

    assert (
        result["same_parity_pairs"] + result["different_parity_pairs"]
        == result["pair_count"]
    )


def test_single_sample_rejected():
    image = np.array([42], dtype=np.uint8)
    with pytest.raises(spa.SpaError):
        spa.analyze(image)


def test_wrong_dtype_rejected():
    image = np.zeros((8, 8), dtype=np.int32)
    with pytest.raises(spa.SpaError):
        spa.analyze(image)
