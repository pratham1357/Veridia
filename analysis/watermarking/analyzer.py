from analysis.core import AnalysisResult, Analyzer, EvidenceInput


class WatermarkAnalyzer(Analyzer):
    """Digital watermark embedding/extraction/verification.

    Interface placeholder. Not yet implemented.
    """

    name = "watermarking"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        raise NotImplementedError("WatermarkAnalyzer is not implemented yet.")
