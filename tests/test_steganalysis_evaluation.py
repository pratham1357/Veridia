import numpy as np
import pytest

from analysis.steganography.evaluation import evaluate_detector


def test_evaluates_multiple_payload_rates():
    rng = np.random.default_rng(7)
    covers = [
        rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
        for _ in range(4)
    ]
    stego_by_rate = {
        0.1: [image.copy() for image in covers],
        0.5: [image.copy() for image in covers],
    }

    # Deterministic fake detector for validating evaluation arithmetic.
    def detector(image):
        return float(image[0, 0, 0] >= 128)

    result = evaluate_detector(
        covers, stego_by_rate, detector=detector, threshold=0.5
    )

    assert len(result["results"]) == 2
    assert result["results"][0]["payload_rate"] == 0.1
    assert result["results"][1]["payload_rate"] == 0.5
    assert 0 <= result["results"][0]["detection_rate"] <= 1
    assert 0 <= result["results"][0]["false_positive_rate"] <= 1


def test_false_positive_rate_is_calculated():
    covers = [
        np.full((4, 4), value, dtype=np.uint8)
        for value in (0, 1, 2, 3)
    ]
    stego = {0.2: [np.full((4, 4), 255, dtype=np.uint8)]}

    result = evaluate_detector(
        covers, stego,
        detector=lambda image: float(image[0, 0] >= 2),
        threshold=0.5,
    )

    assert result["results"][0]["false_positive_rate"] == 0.5
    assert result["results"][0]["detection_rate"] == 1.0


def test_empty_cover_images_rejected():
    with pytest.raises(ValueError):
        evaluate_detector([], {0.1: [np.zeros((8, 8), dtype=np.uint8)]})


def test_invalid_payload_rate_rejected():
    image = np.zeros((8, 8), dtype=np.uint8)
    with pytest.raises(ValueError):
        evaluate_detector([image], {0.0: [image]})
