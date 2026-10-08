"""Image-quality metrics comparing an original and a processed image.

Inputs are uint8 arrays of identical shape, e.g. (H, W, 3).
"""

import math

import numpy as np

_L = 255.0  # dynamic range of 8-bit data
_SSIM_WINDOW = 7


def _check(a: np.ndarray, b: np.ndarray) -> None:
    if a.shape != b.shape:
        raise ValueError(f"Image shapes differ: {a.shape} vs {b.shape}")


def mse(original: np.ndarray, processed: np.ndarray) -> float:
    """Mean squared error over all samples. 0 means identical."""
    _check(original, processed)
    diff = original.astype(np.int32) - processed.astype(np.int32)
    return float(np.mean(np.square(diff), dtype=np.float64))


def psnr(original: np.ndarray, processed: np.ndarray) -> float | None:
    """Peak signal-to-noise ratio in dB: 10*log10(255^2 / MSE). ``None`` if the images are identical."""
    error = mse(original, processed)
    if error == 0:
        return None
    return 10.0 * math.log10(_L * _L / error)


def _box_mean(x: np.ndarray, w: int) -> np.ndarray:
    """Mean over every w x w window (valid positions only), via an integral image."""
    c = np.zeros((x.shape[0] + 1, x.shape[1] + 1), dtype=np.float64)
    c[1:, 1:] = x.cumsum(axis=0).cumsum(axis=1)
    sums = c[w:, w:] - c[:-w, w:] - c[w:, :-w] + c[:-w, :-w]
    return sums / (w * w)


def _ssim_channel(a: np.ndarray, b: np.ndarray, w: int) -> float:
    c1, c2 = (0.01 * _L) ** 2, (0.03 * _L) ** 2
    mu_a, mu_b = _box_mean(a, w), _box_mean(b, w)
    var_a = _box_mean(a * a, w) - mu_a**2
    var_b = _box_mean(b * b, w) - mu_b**2
    cov = _box_mean(a * b, w) - mu_a * mu_b
    ssim_map = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / ((mu_a**2 + mu_b**2 + c1) * (var_a + var_b + c2))
    return float(ssim_map.mean())


def ssim(original: np.ndarray, processed: np.ndarray) -> float:
    """Mean structural similarity (Wang et al., 2004), averaged over channels.

    Uses a uniform 7x7 sliding window (the reference implementation uses a Gaussian
    window), so values can differ slightly from other libraries. 1.0 means identical.
    """
    _check(original, processed)
    a = original.astype(np.float64)
    b = processed.astype(np.float64)
    if a.ndim == 2:
        a, b = a[..., None], b[..., None]
    w = min(_SSIM_WINDOW, a.shape[0], a.shape[1])
    return float(np.mean([_ssim_channel(a[..., i], b[..., i], w) for i in range(a.shape[2])]))


def compare_images(original: np.ndarray, processed: np.ndarray) -> dict[str, float | None]:
    return {"mse": mse(original, processed), "psnr_db": psnr(original, processed), "ssim": ssim(original, processed)}


def difference_map(original: np.ndarray, processed: np.ndarray) -> tuple[np.ndarray, int]:
    """Visualise where two images differ.

    Returns a grayscale image of the per-pixel maximum absolute channel difference,
    stretched so the largest difference maps to 255, and that largest difference.
    The stretch makes +/-1 LSB changes visible; compare magnitudes via the returned
    maximum, not by brightness.
    """
    _check(original, processed)
    diff = np.abs(original.astype(np.int16) - processed.astype(np.int16))
    if diff.ndim == 3:
        diff = diff.max(axis=2)
    peak = int(diff.max())
    if peak == 0:
        return np.zeros(diff.shape, dtype=np.uint8), 0
    return (diff * (255.0 / peak)).astype(np.uint8), peak


def difference_statistics(original: np.ndarray, processed: np.ndarray) -> dict[str, object]:
    """Pixel-level difference measurements between two RGB images of identical shape."""
    _check(original, processed)
    diff = np.abs(original.astype(np.int16) - processed.astype(np.int16))
    changed = diff.max(axis=2) > 0
    peak = int(diff.max()) if diff.size else 0
    return {
        "total_pixels": int(changed.size),
        "changed_pixels": int(changed.sum()),
        "changed_fraction": float(changed.mean()) if changed.size else 0.0,
        "max_abs_difference": peak,
        "mean_abs_difference": float(diff.mean()) if diff.size else 0.0,
        "lsb_only": peak <= 1,
        "changed_samples_per_channel": {name: int(np.count_nonzero(diff[..., i])) for i, name in enumerate(("red", "green", "blue"))},
    }
