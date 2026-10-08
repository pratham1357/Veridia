"""Histogram statistics and the chi-square attack (Westfeld & Pfitzmann, 1999).

Principle: LSB replacement only ever moves a value within its "pair of values"
(2k, 2k+1). Embedding random message bits therefore drives the counts of 2k and
2k+1 towards equality. The chi-square test measures how well the observed even
counts fit the expectation that each pair is perfectly equalised:

    expected_k = (h[2k] + h[2k+1]) / 2
    chi2       = sum_k (h[2k] - expected_k)^2 / expected_k

and reports ``p = P(X >= chi2)`` for a chi-square distribution with (pairs - 1)
degrees of freedom. A p-value close to 1 means the pairs are *consistent with*
equalisation; it is not proof of embedding (very smooth or noisy images can also
have nearly equal pairs).

The test assumes the embedded bits are random-looking (as with encrypted or
compressed data). Plain-text payloads are not: every ASCII byte has a 0 top bit,
so one carrier in eight is forced to 0 and the pairs are *not* equalised. Measured
on a 512x384 test image at 40% of capacity, random bytes gave a consistent prefix
of 50% while ASCII text gave 0%; RS analysis detected both (~40%).

Because the VERIDIA embedder (like many simple tools) writes sequentially, the
test is also run on growing prefixes of the sample stream. A high p-value over an
initial prefix followed by a drop is the classic signature of sequential
embedding of a partial payload.
"""

import math

import numpy as np

CHANNELS = ("red", "green", "blue")
_MIN_EXPECTED = 5  # pairs with fewer expected samples are excluded (chi-square validity)


def channel_histograms(pixels: np.ndarray) -> dict[str, list[int]]:
    return {name: np.bincount(pixels[..., i].ravel(), minlength=256).tolist() for i, name in enumerate(CHANNELS)}


def channel_summary(channel: np.ndarray) -> dict[str, float]:
    hist = np.bincount(channel.ravel(), minlength=256)
    prob = hist[hist > 0] / channel.size
    return {
        "mean": float(channel.mean()),
        "std": float(channel.std()),
        "entropy_bits": float(-(prob * np.log2(prob)).sum()),
    }


def _chi2_sf(x: float, df: int) -> float:
    """Survival function of the chi-square distribution: regularised upper incomplete gamma Q(df/2, x/2)."""
    a, x = df / 2.0, x / 2.0
    if x <= 0:
        return 1.0
    log_prefactor = -x + a * math.log(x) - math.lgamma(a)
    if x < a + 1:  # series expansion of the lower function P
        term = total = 1.0 / a
        ap = a
        for _ in range(10_000):
            ap += 1
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return max(0.0, 1.0 - total * math.exp(log_prefactor))
    # continued fraction for Q (modified Lentz)
    tiny = 1e-300
    b = x + 1 - a
    c, d = 1 / tiny, 1 / b
    h = d
    for i in range(1, 10_000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return min(1.0, math.exp(log_prefactor) * h)


def chi_square_attack(hist: np.ndarray) -> dict[str, float | int | None]:
    """Pair-of-values chi-square test on a 256-bin histogram."""
    even, odd = hist[0::2].astype(np.float64), hist[1::2].astype(np.float64)
    expected = (even + odd) / 2
    keep = expected >= _MIN_EXPECTED
    pairs = int(keep.sum())
    if pairs < 2:
        return {"chi2": None, "degrees_of_freedom": 0, "p_value": None}
    chi2 = float(((even[keep] - expected[keep]) ** 2 / expected[keep]).sum())
    return {"chi2": chi2, "degrees_of_freedom": pairs - 1, "p_value": _chi2_sf(chi2, pairs - 1)}


def chi_square_curve(pixels: np.ndarray, steps: int = 20) -> list[dict[str, float | None]]:
    """p-value over growing prefixes of the row-major RGB sample stream (the LSB embedder's order)."""
    flat = pixels.reshape(-1)
    bounds = np.linspace(0, flat.size, steps + 1).astype(int)
    hist = np.zeros(256, dtype=np.int64)
    curve = []
    for i in range(steps):
        hist += np.bincount(flat[bounds[i] : bounds[i + 1]], minlength=256)
        curve.append({"fraction": round((i + 1) / steps, 4), "p_value": chi_square_attack(hist)["p_value"]})
    return curve


def consistent_prefix(curve: list[dict[str, float | None]], threshold: float = 0.95) -> float:
    """Largest prefix fraction such that every prefix up to it has p > threshold (0 if the first does not)."""
    best = 0.0
    for point in curve:
        if point["p_value"] is None or point["p_value"] <= threshold:
            break
        best = point["fraction"]  # type: ignore[assignment]
    return best
