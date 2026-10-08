"""Per-channel statistics and histograms (R, G, B and grayscale luminance)."""

import numpy as np

CHANNELS = ("red", "green", "blue", "gray")


def luminance(pixels: np.ndarray) -> np.ndarray:
    """BT.601 luma, rounded to 8 bits (the usual 'grayscale' of an RGB image)."""
    return np.clip(np.rint(pixels.astype(np.float64) @ [0.299, 0.587, 0.114]), 0, 255).astype(np.uint8)


def _planes(pixels: np.ndarray) -> dict[str, np.ndarray]:
    return {"red": pixels[..., 0], "green": pixels[..., 1], "blue": pixels[..., 2], "gray": luminance(pixels)}


def channel_statistics(pixels: np.ndarray) -> list[dict[str, float | int | str]]:
    return [
        {
            "channel": name,
            "mean": float(plane.mean()),
            "std": float(plane.std()),
            "min": int(plane.min()),
            "max": int(plane.max()),
        }
        for name, plane in _planes(pixels).items()
    ]


def channel_histograms(pixels: np.ndarray) -> dict[str, list[int]]:
    return {name: np.bincount(plane.ravel(), minlength=256).tolist() for name, plane in _planes(pixels).items()}
