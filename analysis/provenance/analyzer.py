from analysis.core import AnalysisResult, Analyzer, EvidenceInput


class ProvenanceAnalyzer(Analyzer):
    """Origin and history analysis (e.g. reasoning across metadata, compression and derivation history).

    Interface placeholder. The provenance *record* (derived artifacts, operations,
    timeline) is kept by the backend and made tamper-evident with the hash chain in
    ``analysis.provenance.chain``; inferring provenance from image content is not
    implemented yet.
    """

    name = "provenance"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        raise NotImplementedError("ProvenanceAnalyzer is not implemented yet.")
