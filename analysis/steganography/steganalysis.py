"""Aggregated, interpretable LSB steganalysis report.

Combines descriptive statistics with two classical statistical detectors
(chi-square attack, RS analysis). Output is a set of measurements plus
*potential* indicators; the report never states that hidden data is present.

Indicator thresholds are heuristics, documented here so they can be reviewed:
- chi-square p > 0.95: conventional significance level for "pairs consistent with
  equalisation".
- RS estimate > 0.10: RS bias on clean images is typically a few percent, so
  smaller estimates are not distinguished from zero.
"""

from typing import Any

import numpy as np

from analysis.steganography import histogram, lsb, lsb_analysis
from analysis.steganography.rs_analysis import rs_estimate

CHI_P_THRESHOLD = 0.95
RS_THRESHOLD = 0.10

DISCLAIMER = (
    "These measurements may indicate characteristics consistent with LSB embedding, but they do not "
    "independently establish the presence of hidden data. Image content, compression history and noise can "
    "produce similar values, and a small or well-spread payload may produce none."
)


def report(pixels: np.ndarray) -> dict[str, Any]:
    lsb_stats = {s["channel"]: s for s in lsb_analysis.channel_statistics(pixels)}
    channels = []
    for i, name in enumerate(histogram.CHANNELS):
        values = pixels[..., i]
        chi = histogram.chi_square_attack(np.bincount(values.ravel(), minlength=256))
        rs = rs_estimate(values)
        channels.append(
            {
                "channel": name,
                **histogram.channel_summary(values),
                "ones_ratio": lsb_stats[name]["ones_ratio"],
                "transition_ratio": lsb_stats[name]["transition_ratio"],
                "chi_square_p": chi["p_value"],
                "rs": rs,
            }
        )

    overall_chi = histogram.chi_square_attack(np.bincount(pixels.ravel(), minlength=256))
    curve = histogram.chi_square_curve(pixels)
    prefix = histogram.consistent_prefix(curve, CHI_P_THRESHOLD)
    rs_values = [c["rs"]["estimate"] for c in channels if c["rs"]["estimate"] is not None]
    rs_mean = float(np.mean(rs_values)) if rs_values else None
    capacity = lsb.capacity_bytes(pixels)
    header = lsb_analysis.has_veridia_header(pixels)

    return {
        "channels": channels,
        "histograms": histogram.channel_histograms(pixels),
        "chi_square": {**overall_chi, "curve": curve, "consistent_prefix_fraction": prefix},
        "rs_mean_estimate": rs_mean,
        "lsb_capacity_bytes": capacity,
        "prefix_payload_bytes_upper": int(prefix * pixels.size / 8),
        "veridia_lsb_header_found": header,
        "indicators": _indicators(overall_chi["p_value"], prefix, rs_mean, header, pixels.size),
        "disclaimer": DISCLAIMER,
    }


def _indicators(chi_p: float | None, prefix: float, rs_mean: float | None, header: bool, samples: int) -> list[str]:
    notes = []
    if header:
        notes.append(
            "The LSB stream starts with VERIDIA's own payload header. This is a direct format match for this "
            "tool's embedder, not a statistical inference."
        )
    if chi_p is not None and chi_p > CHI_P_THRESHOLD:
        notes.append(
            f"Pair-of-values counts are nearly equalised over the whole image (chi-square p = {chi_p:.3f}), "
            "which is consistent with LSB replacement across most samples."
        )
    elif prefix > 0:
        notes.append(
            f"The first {prefix:.0%} of samples (row-major order) have equalised pair counts (p > {CHI_P_THRESHOLD}) "
            f"while the full image does not. This pattern is consistent with sequential LSB embedding of up to "
            f"about {int(prefix * samples / 8):,} bytes."
        )
    if rs_mean is not None and rs_mean > RS_THRESHOLD:
        notes.append(
            f"RS analysis estimates that about {rs_mean:.0%} of samples carry embedded bits (mean over channels "
            "with a defined estimate)."
        )
    if not notes:
        notes.append(
            "No measurement exceeded the indicator thresholds. This does not establish that the image contains "
            "no hidden data."
        )
    return notes
