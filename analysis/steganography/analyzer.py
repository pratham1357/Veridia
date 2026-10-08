from analysis.core import AnalysisResult, Analyzer, EvidenceInput, Finding, decode_rgb, status_from_findings
from analysis.steganography import steganalysis
from analysis.steganography.steganalysis import CHI_P_THRESHOLD, RS_THRESHOLD

LIMITATIONS = [
    steganalysis.DISCLAIMER,
    "The chi-square attack assumes random-looking message bits (encrypted or compressed data); plain-text payloads often do not equalise pairs.",
    "RS analysis is experimental, has a few percent of bias on clean images and is undefined near full embedding.",
    "Only LSB replacement is modelled; LSB matching (±1) and transform-domain hiding are not.",
]


class SteganographyAnalyzer(Analyzer):
    """LSB steganalysis: channel statistics, chi-square attack and RS analysis, expressed as findings."""

    name = "steganalysis"
    version = "0.3.0"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        report = steganalysis.report(decode_rgb(evidence.data))
        chi = report["chi_square"]
        rs = report["rs_mean_estimate"]
        measurements = {
            "chi_square_p": chi["p_value"],
            "chi_square_consistent_prefix": chi["consistent_prefix_fraction"],
            "rs_mean_estimate": rs,
            "lsb_capacity_bytes": report["lsb_capacity_bytes"],
            "veridia_header_found": report["veridia_lsb_header_found"],
            **{f"lsb_ones_{c['channel']}": round(c["ones_ratio"], 4) for c in report["channels"]},
        }
        data = {k: report[k] for k in ("channels", "histograms", "chi_square")}

        if chi["p_value"] is None and rs is None:
            finding = Finding(
                "Image too small or uniform for statistical tests",
                "Neither the chi-square test nor RS analysis produced a value.",
                "No statistical statement can be made about LSB embedding.",
                "Does not establish whether data is hidden.",
            )
            return AnalysisResult("steganalysis", self.version, "inconclusive", "Statistical tests could not be applied.", measurements, [finding], LIMITATIONS, data)

        findings = self._findings(report)
        status = status_from_findings(findings)
        interpretation = (
            "Measurements are consistent with LSB embedding in this image, but they do not by themselves establish hidden data."
            if status == "indicator_detected"
            else "No LSB steganalysis indicator exceeded its threshold."
        )
        return AnalysisResult("steganalysis", self.version, status, interpretation, measurements, findings, LIMITATIONS, data)

    @staticmethod
    def _findings(report: dict) -> list[Finding]:
        chi = report["chi_square"]
        rs = report["rs_mean_estimate"]
        findings = []
        if report["veridia_lsb_header_found"]:
            findings.append(Finding(
                "VERIDIA LSB payload header present",
                "The first 64 LSBs decode to the magic value 'VRDS' and a valid payload length.",
                "The image very likely carries a payload written by VERIDIA's LSB embedder.",
                "Recognises only this tool's own format; payloads from other tools are not detected this way.",
                "indicator",
            ))
        if chi["p_value"] is not None and chi["p_value"] > CHI_P_THRESHOLD:
            findings.append(Finding(
                "Pair-of-values counts are equalised across the image",
                f"Chi-square p = {chi['p_value']:.3f} (> {CHI_P_THRESHOLD}) over all samples.",
                "Consistent with LSB replacement across most samples.",
                "Very smooth, noisy or synthetic images can also have nearly equal pairs.",
                "indicator",
            ))
        elif chi["consistent_prefix_fraction"] > 0:
            findings.append(Finding(
                "Equalised pairs in an initial portion of the image",
                f"Chi-square p > {CHI_P_THRESHOLD} for the first {chi['consistent_prefix_fraction']:.0%} of samples (row-major), not for the whole image.",
                f"Consistent with sequential LSB embedding of up to about {report['prefix_payload_bytes_upper']:,} bytes.",
                "The prefix boundary is approximate, and content in the top rows can affect it.",
                "indicator",
            ))
        if rs is not None and rs > RS_THRESHOLD:
            findings.append(Finding(
                "RS analysis estimates a non-trivial embedding rate",
                f"Mean RS estimate {rs:.1%} of samples (threshold {RS_THRESHOLD:.0%}).",
                "Consistent with that fraction of samples carrying LSB-embedded bits.",
                "Experimental estimate; image content biases it by a few percent and it can be wrong for unusual images.",
                "indicator",
            ))
        if not findings:
            rs_text = "undefined" if rs is None else f"{rs:.1%}"
            p_text = "n/a" if chi["p_value"] is None else f"{chi['p_value']:.3f}"
            findings.append(Finding(
                "No LSB steganalysis indicator exceeded its threshold",
                f"Chi-square p = {p_text}, consistent prefix {chi['consistent_prefix_fraction']:.0%}, RS estimate {rs_text}.",
                "No statistical sign of LSB replacement was measured.",
                "Does not establish absence of hidden data: small, non-random, ±1 or transform-domain payloads can go undetected.",
            ))
        return findings
