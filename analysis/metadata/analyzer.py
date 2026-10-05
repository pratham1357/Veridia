from analysis.core import AnalysisResult, Analyzer, EvidenceInput


class MetadataAnalyzer(Analyzer):
    """File metadata (e.g. EXIF) extraction and consistency checks.

    Interface placeholder. Not yet implemented.
    """

    name = "metadata"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        raise NotImplementedError("MetadataAnalyzer is not implemented yet.")
