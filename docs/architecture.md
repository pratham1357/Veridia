# Architecture

## Layers

| Layer | Location | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | Investigator UI. Talks only to the backend API. |
| API | `backend/app/api` | HTTP routing and request/response handling. No forensic logic. |
| Schemas | `backend/app/schemas` | Pydantic models, including `EvidenceArtifact`. |
| Services | `backend/app/services` | Planned orchestration between API and analysis. Empty today. |
| Analysis | `analysis/` | Independent forensic analyzers behind a common contract. |

## Analyzer contract

`analysis/core/base.py` defines `Analyzer.analyze(EvidenceInput) -> AnalysisResult`. Each analyzer:

- reads a preserved, read-only copy of the evidence,
- returns explainable indicators (never a bare authentic/fake verdict),
- reports its own name and version for reproducibility,
- lives in its own package so teams can work independently.

| Package | Class |
| --- | --- |
| `analysis/metadata` | `MetadataAnalyzer` |
| `analysis/integrity` | `IntegrityAnalyzer` |
| `analysis/steganography` | `SteganographyAnalyzer` |
| `analysis/watermarking` | `WatermarkAnalyzer` |
| `analysis/provenance` | `ProvenanceAnalyzer` |

All five currently raise `NotImplementedError`.

## Evidence model

`EvidenceArtifact` (`backend/app/schemas/evidence.py`) holds identity (ID, sanitized filename, detected type, size, SHA-256, intake timestamp) and one optional `FindingSet` per analysis area. The TypeScript mirror is `frontend/src/types/evidence.ts`; keep them in sync. There is no persistence layer yet.

## Notes

- `analysis/` is a top-level package, imported by the backend as `analysis.*`. The repository root must be on `PYTHONPATH` when the backend begins using it (`pytest.ini` already does this for tests).
