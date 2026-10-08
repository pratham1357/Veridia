"""Compression characteristics: JPEG quantization tables, quality estimate, 8x8 blockiness.

JPEG quality estimation
-----------------------
Most encoders derive their quantization tables by scaling the example tables in
the JPEG standard (ITU-T T.81 Annex K) with the IJG formula:

    scale = 5000 // Q           for Q < 50   (integer division, as in libjpeg)
    scale = 200 - 2Q            for Q >= 50
    table = clamp(floor((base * scale + 50) / 100), 1, 255)

The estimate is the Q in 1..100 whose scaled table is closest (mean absolute
difference) to the file's table. An exact match means the file was written by an
IJG-style encoder at that quality. A non-zero deviation is typical of camera
firmware and some editors, which use their own tables; the estimate is then only
approximate.

Blockiness
----------
JPEG compresses 8x8 blocks independently, which leaves small luminance steps at
block boundaries. The ratio

    mean |step| across 8x8 boundaries / mean |step| inside blocks

is about 1.0 for images without block structure. Measured on the synthetic test
images used in this project: clean ~1.00, JPEG q95 ~1.13, q75 ~1.74, q50 ~2.1, and
VERIDIA's DCT watermark ~1.36. In a lossless file a raised ratio is therefore a
potential indicator of earlier block-DCT processing. The 1.10 threshold is a
heuristic from those measurements, not a calibrated detector.
"""

import io
from typing import Any

import numpy as np
from PIL import Image, JpegImagePlugin

from analysis.metrics.channels import luminance

STD_LUMINANCE = np.array([
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99,
])  # fmt: skip
STD_CHROMINANCE = np.array([
    17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99, 24, 26, 56, 99, 99, 99, 99, 99,
    47, 66, 99, 99, 99, 99, 99, 99, *[99] * 32,
])  # fmt: skip
BLOCKINESS_THRESHOLD = 1.10
_SUBSAMPLING = {0: "4:4:4", 1: "4:2:2", 2: "4:2:0"}


def scaled_table(base: np.ndarray, quality: int) -> np.ndarray:
    scale = 5000 // quality if quality < 50 else 200 - 2 * quality
    return np.clip(np.floor((base * scale + 50) / 100), 1, 255)


def estimate_quality(table: np.ndarray, base: np.ndarray) -> tuple[int, float]:
    """Best-matching IJG quality and the mean absolute deviation from its table (0 = exact)."""
    errors = [float(np.abs(scaled_table(base, q) - table).mean()) for q in range(1, 101)]
    best = int(np.argmin(errors))
    return best + 1, errors[best]


def jpeg_info(data: bytes) -> dict[str, Any] | None:
    """Quantization tables and related characteristics, or ``None`` if the file is not a JPEG."""
    with Image.open(io.BytesIO(data)) as img:
        if img.format != "JPEG":
            return None
        tables = {int(k): [int(v) for v in t] for k, t in getattr(img, "quantization", {}).items()}
        sampling = JpegImagePlugin.get_sampling(img)
        progressive = bool(img.info.get("progressive") or img.info.get("progression"))
    luma = np.array(tables[0]) if 0 in tables else None
    chroma = np.array(tables[1]) if 1 in tables else None
    q_luma, dev_luma = estimate_quality(luma, STD_LUMINANCE) if luma is not None and luma.size == 64 else (None, None)
    q_chroma, dev_chroma = estimate_quality(chroma, STD_CHROMINANCE) if chroma is not None and chroma.size == 64 else (None, None)
    return {
        "tables": tables,  # natural (row-major) order, 64 values each
        "table_count": len(tables),
        "quality_estimate_luminance": q_luma,
        "quality_deviation_luminance": dev_luma,
        "quality_estimate_chrominance": q_chroma,
        "quality_deviation_chrominance": dev_chroma,
        "standard_tables": dev_luma == 0.0 and dev_chroma in (0.0, None),
        "subsampling": _SUBSAMPLING.get(sampling, "unknown"),
        "progressive": progressive,
    }


def blockiness(pixels: np.ndarray) -> float | None:
    """Ratio of luminance steps across 8x8 block boundaries to steps inside blocks (~1.0 = no block structure)."""
    if pixels.shape[0] < 16 or pixels.shape[1] < 16:
        return None
    g = luminance(pixels).astype(np.float64)
    dh, dv = np.abs(np.diff(g, axis=1)), np.abs(np.diff(g, axis=0))
    edge_h = (np.arange(dh.shape[1]) % 8) == 7
    edge_v = (np.arange(dv.shape[0]) % 8) == 7
    inside = dh[:, ~edge_h].mean() + dv[~edge_v].mean()
    if inside == 0:
        return None
    return float((dh[:, edge_h].mean() + dv[edge_v].mean()) / inside)
