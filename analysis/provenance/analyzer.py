from analysis.core import AnalysisResult, Analyzer, EvidenceInput


class ProvenanceAnalyzer(Analyzer):
    """Origin and history analysis.

    Interface placeholder. Not yet implemented.
    """

    name = "provenance"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        raise NotImplementedError("ProvenanceAnalyzer is not implemented yet.")
