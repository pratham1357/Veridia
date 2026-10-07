"""LSB-plane inspection.

These are descriptive measurements of the least-significant-bit planes. They are
potential indicators only: natural images, noise, and prior processing can all
produce unusual LSB characteristics, and a low-rate payload may produce none.
"""

import numpy as np

from analysis.steganography import lsb

CHANNELS = ("red", "green", "blue")


def lsb_plane(pixels: np.ndarray, channel: str) -> np.ndarray:
    """2-D array of 0/1 values: the LSB of one colour channel."""
    return pixels[..., CHANNELS.index(channel)] & 1


def lsb_plane_image(pixels: np.ndarray, channel: str) -> np.ndarray:
    """Grayscale rendering of an LSB plane (0 -> black, 1 -> white)."""
    return (lsb_plane(pixels, channel) * 255).astype(np.uint8)


def channel_statistics(pixels: np.ndarray) -> list[dict[str, float | str]]:
    """Per-channel LSB measurements.

    - ``ones_ratio``: fraction of LSBs equal to 1.
    - ``transition_ratio``: fraction of horizontally adjacent LSB pairs that differ.
      A random bit plane gives about 0.5; smooth natural images often differ.
    """
    stats = []
    for name in CHANNELS:
        plane = lsb_plane(pixels, name)
        transitions = float(np.mean(plane[:, 1:] != plane[:, :-1])) if plane.shape[1] > 1 else 0.0
        stats.append({"channel": name, "ones_ratio": float(plane.mean()), "transition_ratio": transitions})
    return stats


def has_veridia_header(pixels: np.ndarray) -> bool:
    """True if the LSB stream starts with a valid VERIDIA LSB payload header."""
    try:
        lsb.extract(pixels)
    except lsb.NoPayloadError:
        return False
    return True
