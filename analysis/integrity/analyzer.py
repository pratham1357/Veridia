from analysis.core import AnalysisResult, Analyzer, EvidenceInput


class IntegrityAnalyzer(Analyzer):
    """Image integrity and manipulation indicators.

    Interface placeholder. Not yet implemented.
    """

    name = "integrity"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        raise NotImplementedError("IntegrityAnalyzer is not implemented yet.")
