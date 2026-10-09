"""Evaluation harness for steganalysis detectors.

Measures detection rate and false-positive rate against labeled cover/stego
samples. The SPA statistic used here is experimental, not a calibrated detector.
"""

from typing import Callable

import numpy as np

from analysis.steganography import spa


def spa_score(image: np.ndarray) -> float:
    """Return the experimental adjacent-pair score."""
    return float(spa.analyze(image)["score"])


def evaluate_detector(
    cover_images: list[np.ndarray],
    stego_images_by_rate: dict[float, list[np.ndarray]],
    detector: Callable[[np.ndarray], float] = spa_score,
    threshold: float = 0.05,
) -> dict:
    """Evaluate cover/stego images at each payload rate.

    A score >= threshold is classified as stego.
    Detection rate = correctly flagged stego images / all stego images.
    False-positive rate = cover images incorrectly flagged / all cover images.
    """
    if not cover_images:
        raise ValueError("At least one cover image is required.")
    if not stego_images_by_rate:
        raise ValueError("Provide stego images for at least one payload rate.")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0 and 1.")

    cover_scores = [float(detector(image)) for image in cover_images]
    false_positives = sum(score >= threshold for score in cover_scores)
    false_positive_rate = false_positives / len(cover_scores)

    results = []
    for payload_rate, stego_images in sorted(stego_images_by_rate.items()):
        if not 0.0 < payload_rate <= 1.0:
            raise ValueError("Payload rates must be in (0, 1].")
        if not stego_images:
            raise ValueError(f"No stego images supplied for rate {payload_rate}.")

        scores = [float(detector(image)) for image in stego_images]
        true_positives = sum(score >= threshold for score in scores)

        results.append({
            "payload_rate": float(payload_rate),
            "cover_count": len(cover_images),
            "stego_count": len(stego_images),
            "threshold": float(threshold),
            "detection_rate": true_positives / len(scores),
            "false_positive_rate": false_positive_rate,
            "cover_mean_score": float(np.mean(cover_scores)),
            "stego_mean_score": float(np.mean(scores)),
            "cover_scores": cover_scores,
            "stego_scores": scores,
            "detector": "experimental_adjacent_pair_parity_screen",
        })

    return {
        "evaluation": "cover_vs_stego",
        "results": results,
        "warning": (
            "Results describe this dataset and threshold only. "
            "The current SPA score is experimental and is not a validated "
            "classical SPA payload estimator."
        ),
    }
