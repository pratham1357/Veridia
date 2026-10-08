from analysis.core import AnalysisResult, Analyzer, EvidenceInput, decode_rgb
from analysis.steganography import steganalysis


class SteganographyAnalyzer(Analyzer):
    """LSB steganalysis: channel statistics, chi-square attack and RS analysis."""

    name = "steganography"
    version = "0.2.0"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        result = steganalysis.report(decode_rgb(evidence.path.read_bytes()))
        notes = [*result.pop("indicators"), result.pop("disclaimer")]
        return AnalysisResult(self.name, self.version, indicators=[result], notes=notes)
