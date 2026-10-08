from analysis.core import AnalysisResult, Analyzer, EvidenceInput, Finding, decode_rgb, probe, sha256_hex, status_from_findings
from analysis.integrity.compression import BLOCKINESS_THRESHOLD, blockiness, jpeg_info
from analysis.metrics import channel_histograms, channel_statistics

LIMITATIONS = [
    "These are descriptive measurements of the file and its pixels. None of them establishes whether the image content is authentic.",
    "Hash verification covers the period since the file entered VERIDIA, not its history before acquisition.",
    f"The blockiness threshold ({BLOCKINESS_THRESHOLD}) is a heuristic derived from synthetic test images, not a calibrated detector.",
]


class IntegrityAnalyzer(Analyzer):
    """File integrity (hash), image characteristics and compression characteristics."""

    name = "integrity"
    version = "0.1.0"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        current = sha256_hex(evidence.data)
        fmt, width, height = probe(evidence.data)
        pixels = decode_rgb(evidence.data)
        jpeg = jpeg_info(evidence.data)
        block = blockiness(pixels)

        measurements = {
            "sha256_recorded": evidence.sha256,
            "sha256_current": current,
            "hash_match": current == evidence.sha256,
            "file_size": len(evidence.data),
            "format": fmt,
            "width": width,
            "height": height,
            "blockiness": round(block, 4) if block is not None else None,
            "jpeg_quality_estimate": jpeg["quality_estimate_luminance"] if jpeg else None,
            "jpeg_standard_tables": jpeg["standard_tables"] if jpeg else None,
            "jpeg_subsampling": jpeg["subsampling"] if jpeg else None,
            "jpeg_progressive": jpeg["progressive"] if jpeg else None,
        }
        findings = [self._hash_finding(evidence.sha256, current)]
        findings += self._compression_findings(fmt, jpeg, block)

        status = status_from_findings(findings)
        interpretation = (
            "Hash verified; no compression-related indicator observed."
            if status == "no_indicator"
            else "One or more potential indicators were observed; see findings for what each does and does not establish."
        )
        return AnalysisResult(
            "integrity",
            self.version,
            status,
            interpretation,
            measurements,
            findings,
            LIMITATIONS,
            data={"channels": channel_statistics(pixels), "histograms": channel_histograms(pixels), "jpeg": jpeg},
        )

    @staticmethod
    def _hash_finding(recorded: str, current: str) -> Finding:
        if current == recorded:
            return Finding(
                "Stored bytes match the recorded SHA-256",
                f"SHA-256 recomputed now equals the value recorded on entry ({current[:16]}…).",
                "The file has not changed since it entered VERIDIA.",
                "Says nothing about what happened to the image before acquisition.",
                "verification",
            )
        return Finding(
            "Stored bytes do not match the recorded SHA-256",
            f"Recorded {recorded[:16]}…, recomputed {current[:16]}….",
            "The stored file changed after acquisition.",
            "Does not show what changed or why.",
            "indicator",
        )

    @staticmethod
    def _compression_findings(fmt: str, jpeg: dict | None, block: float | None) -> list[Finding]:
        findings: list[Finding] = []
        if jpeg is not None:
            q, dev = jpeg["quality_estimate_luminance"], jpeg["quality_deviation_luminance"]
            findings.append(
                Finding(
                    "Image is JPEG compressed",
                    f"{jpeg['table_count']} quantization table(s) present; luminance table closest to IJG quality {q} "
                    f"(mean deviation {dev:.2f}); chroma subsampling {jpeg['subsampling']}.",
                    "The pixel data has been lossy-compressed at least once.",
                    "JPEG compression alone does not establish manipulation; most cameras and platforms save JPEG.",
                )
            )
            if not jpeg["standard_tables"]:
                findings.append(
                    Finding(
                        "Quantization tables are not standard IJG tables",
                        f"Best-matching IJG quality {q} still deviates by {dev:.2f} on average.",
                        "Typical of camera firmware or encoders with custom tables; the quality figure is approximate.",
                        "Table origin alone cannot identify the device or software.",
                    )
                )
        else:
            findings.append(
                Finding(
                    f"Lossless format ({fmt}): no JPEG quantization tables",
                    f"The file is {fmt}, which stores pixels without lossy quantization.",
                    "The current file was not JPEG-encoded.",
                    "The pixels may still have been JPEG-compressed before being saved losslessly.",
                )
            )
            if block is not None and block > BLOCKINESS_THRESHOLD:
                findings.append(
                    Finding(
                        "8×8 block-aligned discontinuities in a lossless file",
                        f"Blockiness ratio {block:.3f} (about 1.0 without block structure; threshold {BLOCKINESS_THRESHOLD}).",
                        "Consistent with earlier JPEG compression or other block-DCT processing (e.g. DCT watermarking) before the file was saved losslessly.",
                        "Heuristic: textures aligned with the 8-pixel grid or resampling can also raise the ratio, and it cannot identify or date the processing.",
                        "indicator",
                    )
                )
        return findings
