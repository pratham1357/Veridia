from analysis.core import AnalysisResult, Analyzer, EvidenceInput, decode_rgb
from analysis.steganography import lsb_analysis


class SteganographyAnalyzer(Analyzer):
    """Reports LSB-plane characteristics. Statistical steganalysis is not implemented yet."""

    name = "steganography"
    version = "0.1.0"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        pixels = decode_rgb(evidence.path.read_bytes())
        return AnalysisResult(
            self.name,
            self.version,
            indicators=[
                {"channels": lsb_analysis.channel_statistics(pixels)},
                {"veridia_lsb_header_found": lsb_analysis.has_veridia_header(pixels)},
            ],
            notes=["LSB characteristics are descriptive measurements, not proof of hidden data."],
        )
