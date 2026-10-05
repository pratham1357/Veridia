from analysis.core import AnalysisResult, Analyzer, EvidenceInput


class SteganographyAnalyzer(Analyzer):
    """Hidden-information indicators.

    Interface placeholder. Not yet implemented.
    """

    name = "steganography"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        raise NotImplementedError("SteganographyAnalyzer is not implemented yet.")
