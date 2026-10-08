"""Block DCT primitives (implemented directly with NumPy, no external DCT library).

The 8x8 two-dimensional DCT-II used by JPEG is separable: for an orthonormal
DCT matrix ``D`` (rows = cosine basis vectors), the transform of block ``B`` is
``D @ B @ D.T`` and the inverse is ``D.T @ C @ D``. Coefficient ``C[u, v]`` is
the weight of the basis pattern with vertical frequency ``u`` and horizontal
frequency ``v``; ``C[0, 0]`` is the block's DC (mean) term.
"""

import numpy as np

BLOCK = 8


def dct_matrix(n: int = BLOCK) -> np.ndarray:
    k = np.arange(n)
    d = np.sqrt(2.0 / n) * np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    d[0, :] = np.sqrt(1.0 / n)
    return d


_D = dct_matrix()


def to_blocks(channel: np.ndarray) -> np.ndarray:
    """(H, W) -> (H/8, W/8, 8, 8). H and W must be multiples of 8."""
    h, w = channel.shape
    return channel.reshape(h // BLOCK, BLOCK, w // BLOCK, BLOCK).swapaxes(1, 2)


def from_blocks(blocks: np.ndarray) -> np.ndarray:
    bh, bw = blocks.shape[:2]
    return blocks.swapaxes(1, 2).reshape(bh * BLOCK, bw * BLOCK)


def block_dct(channel: np.ndarray) -> np.ndarray:
    """Forward 8x8 DCT of every block of a float channel cropped to a multiple of 8."""
    return _D @ to_blocks(channel) @ _D.T


def block_idct(coeffs: np.ndarray) -> np.ndarray:
    return from_blocks(_D.T @ coeffs @ _D)


# ITU-R BT.601 (JFIF) colour transform. Watermarking uses the luminance (Y) channel.


def rgb_to_ycbcr(rgb: np.ndarray) -> np.ndarray:
    m = np.array([[0.299, 0.587, 0.114], [-0.168736, -0.331264, 0.5], [0.5, -0.418688, -0.081312]])
    ycc = rgb.astype(np.float64) @ m.T
    ycc[..., 1:] += 128.0
    return ycc


def ycbcr_to_rgb(ycc: np.ndarray) -> np.ndarray:
    y, cb, cr = ycc[..., 0], ycc[..., 1] - 128.0, ycc[..., 2] - 128.0
    rgb = np.stack([y + 1.402 * cr, y - 0.344136 * cb - 0.714136 * cr, y + 1.772 * cb], axis=-1)
    return np.clip(np.rint(rgb), 0, 255).astype(np.uint8)


def dct_magnitude_map(pixels: np.ndarray) -> np.ndarray:
    """Visualisation: log-magnitude of each 8x8 block's DCT on luminance, scaled to 0-255.

    Each 8x8 tile of the output shows that block's coefficients (DC top-left,
    increasing horizontal frequency to the right, vertical frequency downwards).
    """
    y = rgb_to_ycbcr(pixels)[..., 0]
    h, w = (y.shape[0] // BLOCK) * BLOCK, (y.shape[1] // BLOCK) * BLOCK
    mag = np.log1p(np.abs(from_blocks(block_dct(y[:h, :w] - 128.0))))
    top = mag.max() or 1.0
    return (255 * mag / top).astype(np.uint8)
