"""Sample Pair Analysis (SPA) for LSB steganalysis.

This implementation provides a simple adjacent-pair statistical score.
It is an exploratory detector, not a complete calibrated SPA estimator.
It should not be treated as definitive proof that an image contains hidden data.
"""

import numpy as np


class SpaError(ValueError):
    """Invalid input for SPA analysis."""


def _validate_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise SpaError("Image must be a NumPy array.")
    if image.dtype != np.uint8:
        raise SpaError("Image must have dtype uint8.")
    if image.ndim not in (1, 2, 3) or image.size == 0:
        raise SpaError("Image must be a non-empty 1D, grayscale, or color array.")



def analyze(image: np.ndarray) -> dict:
    """Compute an exploratory sample-pair statistic for an image.

    Returns a score and the measured adjacent-pair counts. The score is not
    a probability and must not be interpreted as a calibrated detection rate.
    """
    _validate_image(image)

    values = image.reshape(-1).astype(np.int16)
    if values.size < 2:
        raise SpaError("At least two samples are required.")

    # Adjacent samples with matching parity and differing parity.
    left = values[:-1]
    right = values[1:]
    same_parity = ((left & 1) == (right & 1))
    different_parity = ~same_parity

    same_count = int(np.count_nonzero(same_parity))
    different_count = int(np.count_nonzero(different_parity))
    total = same_count + different_count

    same_rate = same_count / total
    different_rate = different_count / total

    # Descriptive deviation from a 50/50 parity split.
    score = abs(same_rate - 0.5) * 2.0

    return {
        "method": "adjacent_pair_parity_screen",
        "sample_count": int(values.size),
        "pair_count": int(total),
        "same_parity_pairs": same_count,
        "different_parity_pairs": different_count,
        "same_parity_rate": float(same_rate),
        "different_parity_rate": float(different_rate),
        "score": float(score),
        "interpretation": (
            "Exploratory statistic only; not a calibrated SPA estimate "
            "or proof of hidden data."
        ),
    }
