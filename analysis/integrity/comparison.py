"""Forensic comparison of a reference image and a subject (derived or suspected) image."""

from analysis.core import AnalysisResult, EvidenceInput, Finding, decode_rgb
from analysis.metrics import channel_histograms, channel_statistics, compare_images, difference_statistics

VERSION = "0.1.0"
LIMITATIONS = [
    "A comparison measures how two images differ; it does not show which one is the original or why they differ.",
    "Pixel comparison requires identical dimensions and alignment; no registration is performed.",
    "Metadata differences are not part of this comparison.",
]


def compare(reference: EvidenceInput, subject: EvidenceInput) -> AnalysisResult:
    if reference.sha256 == subject.sha256 and reference.data == subject.data:
        return AnalysisResult(
            "comparison", VERSION, "verified", "The two files are byte-identical.",
            {"hashes_identical": True},
            [Finding(
                "Files are byte-identical",
                f"Both files have SHA-256 {subject.sha256[:16]}….",
                "The subject is an exact copy of the reference.",
                "Says nothing about either file's history before they were acquired.",
                "verification",
            )],
            LIMITATIONS,
        )

    a, b = decode_rgb(reference.data), decode_rgb(subject.data)
    if a.shape != b.shape:
        return AnalysisResult(
            "comparison", VERSION, "not_applicable", "The images have different dimensions, so a pixel comparison is not possible.",
            {"hashes_identical": False, "reference_size": f"{a.shape[1]}x{a.shape[0]}", "subject_size": f"{b.shape[1]}x{b.shape[0]}"},
            [Finding(
                "Image dimensions differ",
                f"Reference {a.shape[1]}×{a.shape[0]}, subject {b.shape[1]}×{b.shape[0]}.",
                "The subject may have been resized or cropped, or the images may be unrelated.",
                "Without registration, VERIDIA cannot compare them pixel by pixel.",
            )],
            LIMITATIONS,
        )

    metrics = compare_images(a, b)
    diff = difference_statistics(a, b)
    measurements = {
        "hashes_identical": False,
        "mse": metrics["mse"],
        "psnr_db": metrics["psnr_db"],
        "ssim": metrics["ssim"],
        "changed_pixels": diff["changed_pixels"],
        "total_pixels": diff["total_pixels"],
        "changed_fraction": diff["changed_fraction"],
        "max_abs_difference": diff["max_abs_difference"],
        "mean_abs_difference": diff["mean_abs_difference"],
        "lsb_only": diff["lsb_only"],
    }
    findings = []
    if diff["changed_pixels"] == 0:
        findings.append(Finding(
            "Files differ but decoded pixels are identical",
            "SHA-256 values differ; all pixel values are equal.",
            "Only the encoding or container differs (e.g. re-saved losslessly or metadata changed).",
            "Does not reveal what changed in the container.",
        ))
        status, summary = "no_indicator", "The files differ but their pixels are identical."
    else:
        psnr = "∞" if metrics["psnr_db"] is None else f"{metrics['psnr_db']:.2f} dB"
        findings.append(Finding(
            "Pixel content differs",
            f"{diff['changed_pixels']:,} of {diff['total_pixels']:,} pixels changed ({diff['changed_fraction']:.2%}); "
            f"max |Δ| = {diff['max_abs_difference']}; MSE {metrics['mse']:.4f}, PSNR {psnr}, SSIM {metrics['ssim']:.4f}.",
            "If the images are related, the subject is a modified version of the reference (or vice versa).",
            "Measures the size of the difference, not its intent; visually imperceptible changes can still be large in number.",
            "indicator",
        ))
        if diff["lsb_only"]:
            findings.append(Finding(
                "All changes are ±1 (least significant bit level)",
                f"Maximum absolute difference is 1 across {sum(diff['changed_samples_per_channel'].values()):,} changed samples.",
                "Consistent with LSB steganography or LSB watermarking.",
                "Other ±1 processes (e.g. some rounding or dithering) produce the same pattern.",
                "indicator",
            ))
        status, summary = "indicator_detected", "The subject's pixels differ from the reference; see findings for the measured extent."

    return AnalysisResult(
        "comparison", VERSION, status, summary, measurements, findings, LIMITATIONS,
        data={
            "difference": diff,
            "reference": {"channels": channel_statistics(a), "histograms": channel_histograms(a)},
            "subject": {"channels": channel_statistics(b), "histograms": channel_histograms(b)},
        },
    )
