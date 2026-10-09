"""Error Level Analysis (ELA). Experimental.

Method (after Krawetz, 2007)
----------------------------
The image is re-encoded once as JPEG at a fixed quality Q and decoded again.
The per-pixel *error level* is the largest absolute change over R, G and B:

    E(x, y) = max_c |I(x, y, c) - JPEG_Q(I)(x, y, c)|

JPEG quantisation is close to idempotent: pixels that were already quantised
at a similar quality change little when re-encoded, while content that was not
(e.g. pasted in after the last compression, or never compressed) changes more.
Regions whose error level differs from the rest of the image can therefore point
at a different compression history.

Block statistics
----------------
E is averaged over square blocks aligned to the 8x8 JPEG grid (16 px, or larger
for big images so the grid stays at most 64 blocks per side). Each block mean is
scored against the whole image with a robust z-score,

    z = 0.6745 * (block - median) / MAD          (Iglewicz & Hoaglin)

with the MAD floored at ``MAD_FLOOR`` so that an almost uniform image does not
turn tiny differences into huge scores. Blocks with z > ``Z_THRESHOLD`` are
*outlier blocks*; 4-connected outlier blocks are reported as clusters with a
bounding box. Clusters are found with a breadth-first search (no SciPy).

Calibration and limitations
---------------------------
On the synthetic test images used in this project (a JPEG q75 image with a
64x64 region pasted from an uncompressed source, then saved losslessly or as
JPEG q95), every block of the pasted region scored z > 10 and was flagged. The
same images *without* a splice still produce outlier blocks along hard, high-
contrast edges: ELA responds to edges, fine texture, noise and saturated colour
as strongly as to compression history. ``Z_THRESHOLD`` = 6 is a heuristic from
those measurements, not a calibrated detector, and ELA is reported as a
potential indicator only.
"""

import io
from collections import deque
from typing import Any

import numpy as np
from PIL import Image

from analysis.core import AnalysisResult, Analyzer, EvidenceInput, Finding, decode_rgb

VERSION = "0.1.0"
DEFAULT_QUALITY = 90
MIN_QUALITY, MAX_QUALITY = 50, 99
Z_THRESHOLD = 6.0
MAD_FLOOR = 0.25  # error-level units (0-255 scale)
MIN_BLOCK = 16
MAX_GRID = 64  # blocks per side
MIN_BLOCKS = 16  # fewer blocks than this: statistics are meaningless
FLAT_ERROR = 0.5  # every block mean below this: recompression changes (almost) nothing

LIMITATIONS = [
    "Experimental. The outlier threshold is a heuristic from synthetic test images, not a calibrated detector.",
    "Hard edges, fine texture, noise and saturated colours raise the error level without any manipulation.",
    "A uniform error level does not show the image is unmodified: an edited image re-saved at one quality can be uniform.",
    "The result depends on the recompression quality; compare several qualities before relying on a pattern.",
    "Pixels are taken from the decoded 8-bit RGB image; alpha is dropped and EXIF orientation is not applied.",
]


def _check_quality(quality: int) -> None:
    if not MIN_QUALITY <= quality <= MAX_QUALITY:
        raise ValueError(f"ELA quality must be between {MIN_QUALITY} and {MAX_QUALITY}.")


def recompression_error(pixels: np.ndarray, quality: int = DEFAULT_QUALITY) -> np.ndarray:
    """Per-pixel error level E (float, H x W): max over channels of |I - JPEG_Q(I)|."""
    _check_quality(quality)
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="JPEG", quality=quality)
    with Image.open(io.BytesIO(buf.getvalue())) as img:
        recompressed = np.asarray(img.convert("RGB"), dtype=np.int16)
    return np.abs(pixels.astype(np.int16) - recompressed).max(axis=-1).astype(np.float64)


def block_size_for(height: int, width: int) -> int:
    """Smallest multiple of 8 (at least 16) that keeps the grid within MAX_GRID blocks per side."""
    return max(MIN_BLOCK, 8 * -(-max(height, width) // (8 * MAX_GRID)))


def ela_map(pixels: np.ndarray, quality: int = DEFAULT_QUALITY) -> tuple[np.ndarray, int]:
    """Error-level image stretched so the largest error is white; returns (uint8 H x W, peak error)."""
    error = recompression_error(pixels, quality)
    peak = int(error.max())
    scaled = error * (255.0 / peak) if peak else error
    return np.clip(np.rint(scaled), 0, 255).astype(np.uint8), peak


def block_means(error: np.ndarray, block: int) -> np.ndarray:
    rows, cols = error.shape[0] // block, error.shape[1] // block
    return error[: rows * block, : cols * block].reshape(rows, block, cols, block).mean(axis=(1, 3))


def robust_z(values: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Robust z-scores against the median and MAD (floored at MAD_FLOOR); returns (z, median, raw MAD)."""
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return 0.6745 * (values - median) / max(mad, MAD_FLOOR), median, mad


def clusters(mask: np.ndarray) -> list[dict[str, int]]:
    """4-connected components of a boolean grid, largest first, with bounding boxes in block units."""
    seen = np.zeros_like(mask, dtype=bool)
    found = []
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        queue, cells = deque([(r0, c0)]), []
        seen[r0, c0] = True
        while queue:
            r, c = queue.popleft()
            cells.append((r, c))
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < mask.shape[0] and 0 <= nc < mask.shape[1] and mask[nr, nc] and not seen[nr, nc]:
                    seen[nr, nc] = True
                    queue.append((nr, nc))
        rs, cs = [r for r, _ in cells], [c for _, c in cells]
        found.append({"blocks": len(cells), "row": int(min(rs)), "col": int(min(cs)),
                      "rows": int(max(rs) - min(rs) + 1), "cols": int(max(cs) - min(cs) + 1)})
    return sorted(found, key=lambda c: (-c["blocks"], c["row"], c["col"]))


def error_level_analysis(pixels: np.ndarray, quality: int = DEFAULT_QUALITY) -> dict[str, Any]:
    """All ELA measurements for one image (see module docstring)."""
    error = recompression_error(pixels, quality)
    height, width = error.shape
    block = block_size_for(height, width)
    means = block_means(error, block)
    if means.size == 0:
        z, median, mad = np.zeros_like(means), 0.0, 0.0
    else:
        z, median, mad = robust_z(means)
    outliers = z > Z_THRESHOLD
    found = clusters(outliers)
    for c in found:  # pixel bounding box for display
        c |= {"x": c["col"] * block, "y": c["row"] * block, "width": c["cols"] * block, "height": c["rows"] * block}
    return {
        "quality": quality,
        "block_size": block,
        "grid_rows": int(means.shape[0]),
        "grid_cols": int(means.shape[1]) if means.ndim == 2 else 0,
        "mean_error": float(error.mean()),
        "peak_error": int(error.max()),
        "median_block_error": median,
        "mad_block_error": mad,
        "max_block_error": float(means.max()) if means.size else 0.0,
        "outlier_blocks": int(outliers.sum()),
        "outlier_fraction": float(outliers.mean()) if means.size else 0.0,
        "z_threshold": Z_THRESHOLD,
        "clusters": found,
        "block_means": np.round(means, 3).tolist(),
        "block_z": np.round(z, 2).tolist(),
    }


class ELAAnalyzer(Analyzer):
    """Error Level Analysis as a common AnalysisResult. Experimental; see the module docstring."""

    name = "ela"
    version = VERSION

    def __init__(self, quality: int = DEFAULT_QUALITY):
        _check_quality(quality)
        self.quality = quality

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        pixels = decode_rgb(evidence.data)
        ela = error_level_analysis(pixels, self.quality)
        blocks = ela["grid_rows"] * ela["grid_cols"]
        measurements = {k: ela[k] for k in (
            "quality", "block_size", "grid_rows", "grid_cols", "peak_error", "outlier_blocks", "z_threshold")}
        measurements |= {
            "mean_error": round(ela["mean_error"], 4),
            "median_block_error": round(ela["median_block_error"], 4),
            "max_block_error": round(ela["max_block_error"], 4),
            "outlier_fraction": round(ela["outlier_fraction"], 4),
            "clusters": len(ela["clusters"]),
            "largest_cluster_blocks": ela["clusters"][0]["blocks"] if ela["clusters"] else 0,
        }
        data = {k: ela[k] for k in ("block_size", "quality", "clusters", "block_means", "block_z")} | {
            "width": int(pixels.shape[1]), "height": int(pixels.shape[0]),
        }

        if blocks < MIN_BLOCKS:
            return AnalysisResult(
                "ela", self.version, "not_applicable",
                f"The image is too small for block statistics ({blocks} block(s) of {ela['block_size']} px; at least {MIN_BLOCKS} needed).",
                measurements, [], LIMITATIONS, data,
            )

        level = Finding(
            f"Recompression error level at JPEG quality {self.quality}",
            f"Mean per-pixel error {ela['mean_error']:.2f}; median block error {ela['median_block_error']:.2f} "
            f"(MAD {ela['mad_block_error']:.2f}); largest block error {ela['max_block_error']:.2f}; peak pixel error {ela['peak_error']} (0–255 scale).",
            "A low, even error level is typical of content already quantised at a similar or coarser JPEG quality; "
            "a high level is typical of content that was never JPEG-compressed or was compressed more finely.",
            "The overall level describes compression history only loosely and does not show whether content was changed.",
        )
        if ela["max_block_error"] < FLAT_ERROR:
            return AnalysisResult(
                "ela", self.version, "inconclusive",
                "Recompression barely changes the image, so ELA has no contrast to show at this quality; try a higher quality.",
                measurements, [level], LIMITATIONS, data,
            )

        findings = [level]
        if ela["outlier_blocks"]:
            top = ela["clusters"][0]
            findings.append(Finding(
                "Blocks with an error level well above the rest of the image",
                f"{ela['outlier_blocks']} of {blocks} blocks ({ela['outlier_fraction']:.1%}) have a robust z-score above "
                f"{Z_THRESHOLD:g}, in {len(ela['clusters'])} connected cluster(s); the largest ({top['blocks']} block(s)) spans "
                f"x {top['x']}–{top['x'] + top['width']}, y {top['y']}–{top['y'] + top['height']} px.",
                "These regions respond to recompression differently from the rest of the image. That is consistent with a "
                "different compression history (e.g. content inserted after the last JPEG save), and equally with strong edges or texture.",
                "Experimental heuristic: edges, texture, noise and saturated colour produce the same pattern. Inspect the map and "
                "corroborate with other techniques; ELA alone does not establish manipulation.",
                "indicator",
            ))
            status, summary = "indicator_detected", (
                f"{ela['outlier_blocks']} block(s) stand out in the error-level map; this is a potential indicator that needs visual "
                "inspection and corroboration, not a finding of manipulation."
            )
        else:
            status, summary = "no_indicator", (
                f"No block's error level exceeds the outlier threshold (robust z > {Z_THRESHOLD:g}) at quality {self.quality}."
            )
        return AnalysisResult("ela", self.version, status, summary, measurements, findings, LIMITATIONS, data)
