"""Shared analyzer contract and the common analysis-result structure.

Analyzers receive the exact preserved bytes of an image and return an
``AnalysisResult``. They must not modify or execute the input, and they never
return an authentic/fake verdict. Instead every result has:

- ``status``: one of the categories below
- ``measurements``: the actual numbers or values computed
- ``findings``: each pairs a statement with the measurement supporting it, what
  it may indicate, and what it does *not* establish
- ``interpretation``: a one-sentence summary
- ``limitations``: caveats that apply to the analysis as a whole

Status categories:

- ``verified``           a check with a definite answer succeeded (e.g. watermark matches)
- ``indicator_detected`` at least one potential indicator was observed
- ``no_indicator``       the analysis ran and observed no indicator
- ``inconclusive``       the analysis ran but could not reach a usable result
- ``not_applicable``     the analysis does not apply to this input
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Status = Literal["verified", "indicator_detected", "no_indicator", "inconclusive", "not_applicable"]
FindingKind = Literal["observation", "indicator", "verification"]
Measurement = str | int | float | bool | None


@dataclass(frozen=True)
class EvidenceInput:
    image_id: str
    data: bytes  # exact preserved bytes; read-only
    sha256: str  # hash recorded when the image entered VERIDIA
    filename: str = ""


@dataclass(frozen=True)
class Finding:
    finding: str  # concise statement
    evidence: str  # the measurement that supports it
    interpretation: str  # what it may indicate
    limitation: str  # what it does NOT establish
    kind: FindingKind = "observation"


@dataclass
class AnalysisResult:
    analysis_type: str
    analyzer_version: str
    status: Status
    interpretation: str
    measurements: dict[str, Measurement] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)  # bulky structured output (histograms, tables) for display
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def status_from_findings(findings: list[Finding]) -> Status:
    """``indicator_detected`` if any finding is an indicator, otherwise ``no_indicator``."""
    return "indicator_detected" if any(f.kind == "indicator" for f in findings) else "no_indicator"


class Analyzer(ABC):
    name: str
    version: str = "0.0.0"

    @abstractmethod
    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        """Return measurements and findings; never a bare authentic/fake verdict."""
