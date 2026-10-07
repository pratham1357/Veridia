from analysis.core import AnalysisResult, Analyzer, EvidenceInput
from analysis.metadata.extract import extract_metadata


class MetadataAnalyzer(Analyzer):
    """Reports image header and EXIF metadata. Consistency checks are not implemented yet."""

    name = "metadata"
    version = "0.1.0"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        metadata = extract_metadata(evidence.path.read_bytes())
        return AnalysisResult(self.name, self.version, indicators=[metadata])
