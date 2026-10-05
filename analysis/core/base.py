"""Shared analyzer contract.

Analyzers receive a read-only reference to preserved evidence and return
explainable indicators. They must not modify or execute the evidence.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidenceInput:
    evidence_id: str
    path: Path  # read-only copy of the preserved original
    sha256: str


@dataclass
class AnalysisResult:
    analyzer: str
    analyzer_version: str
    indicators: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class Analyzer(ABC):
    name: str
    version: str = "0.0.0"

    @abstractmethod
    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        """Return forensic indicators with supporting detail; never a bare authentic/fake verdict."""
