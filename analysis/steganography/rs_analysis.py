"""RS analysis (Fridrich, Goljan & Du, 2001): estimate the fraction of LSB-modified samples.

Experimental detector. The principle:

- Split each channel into groups of 4 horizontally adjacent pixels and measure
  each group's noisiness ``f(G) = sum |x[i+1] - x[i]|``.
- ``F1`` flips the LSB (2k <-> 2k+1); ``F-1`` is the shifted flip (2k-1 <-> 2k).
  Apply ``F1`` to the positions selected by the mask ``M = [0, 1, 1, 0]`` (or
  ``F-1`` for the negative mask ``-M``). A group is *Regular* if ``f`` increases,
  *Singular* if it decreases.
- In a natural image ``R_M ~ R_-M`` and ``S_M ~ S_-M``. Random LSB embedding pulls
  ``R_M`` and ``S_M`` together while ``R_-M`` and ``S_-M`` move apart.
- Measuring the same quantities on the image with all LSBs flipped gives a second
  point on each curve; modelling the curves as quadratic in the embedding rate
  yields the quadratic ``2(d1+d0)x^2 + (d-0 - d-1 - d1 - 3d0)x + d0 - d-0 = 0``,
  whose smaller root ``x`` gives the estimate ``p = x / (x - 1/2)``.

``p`` estimates the fraction of samples whose LSB carries message bits (for a
random payload about half of those actually change). The estimate has a bias of a
few percent on clean images, depends on image content, and is unreliable for
very small, synthetic, or heavily noisy images. It is undefined (None) when the
quadratic has no real root, which typically happens close to full embedding.
Values slightly outside [0, 1] are reported as computed.
"""

import math

import numpy as np

_MASK = np.array([False, True, True, False])


def _flip(values: np.ndarray, direction: int) -> np.ndarray:
    return values ^ 1 if direction == 1 else ((values + 1) ^ 1) - 1


def _smoothness(groups: np.ndarray) -> np.ndarray:
    return np.abs(np.diff(groups, axis=1)).sum(axis=1)


def _regular_singular(groups: np.ndarray, direction: int) -> tuple[float, float]:
    before = _smoothness(groups)
    flipped = groups.copy()
    flipped[:, _MASK] = _flip(flipped[:, _MASK], direction)
    after = _smoothness(flipped)
    return float(np.mean(after > before)), float(np.mean(after < before))


def rs_estimate(channel: np.ndarray) -> dict[str, float | None]:
    """RS statistics and the estimated embedding rate for one 8-bit channel (H, W)."""
    width = (channel.shape[1] // 4) * 4
    groups = channel[:, :width].astype(np.int32).reshape(-1, 4)
    if groups.shape[0] < 16:
        return {"r_m": None, "s_m": None, "r_neg_m": None, "s_neg_m": None, "estimate": None}

    r_m, s_m = _regular_singular(groups, 1)
    r_nm, s_nm = _regular_singular(groups, -1)
    r_m1, s_m1 = _regular_singular(groups ^ 1, 1)
    r_nm1, s_nm1 = _regular_singular(groups ^ 1, -1)

    d0, d1, dn0, dn1 = r_m - s_m, r_m1 - s_m1, r_nm - s_nm, r_nm1 - s_nm1
    a, b, c = 2 * (d1 + d0), dn0 - dn1 - d1 - 3 * d0, d0 - dn0
    x: float | None
    if abs(a) < 1e-12:
        x = -c / b if b else None
    else:
        disc = b * b - 4 * a * c
        # No real root: common near full embedding, where the curves meet and noise makes the
        # discriminant slightly negative. The estimate is then reported as undefined.
        x = None if disc < 0 else min(((-b + s) / (2 * a) for s in (math.sqrt(disc), -math.sqrt(disc))), key=abs)
    estimate = None if x is None or abs(x - 0.5) < 1e-12 else x / (x - 0.5)
    return {"r_m": r_m, "s_m": s_m, "r_neg_m": r_nm, "s_neg_m": s_nm, "estimate": estimate}
