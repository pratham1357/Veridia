# Architecture

## Layers

| Layer | Location | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | Investigator UI. Talks only to the backend API. |
| API | `backend/app/api` | HTTP routing. Thin: validates input and delegates to services. |
| Schemas | `backend/app/schemas` | Pydantic models: `EvidenceArtifact`, `ProvenanceRecord`, request/response models. |
| Services | `backend/app/services` | In-memory store, evidence ingestion, orchestration of analysis and provenance recording. |
| Analysis | `analysis/` | Pure algorithms on bytes/NumPy arrays. No web or storage dependencies. |

Frontend types in `frontend/src/types/evidence.ts` mirror the Pydantic schemas; keep them in sync.

## Analysis package

| Package | Contents | Status |
| --- | --- | --- |
| `core` | `sha256_hex`, image decode/encode (`decode_rgb`, `encode_png`, `probe`), `Analyzer` contract | Implemented |
| `metadata` | `extract_metadata`, `MetadataAnalyzer` | Implemented |
| `steganography` | `lsb` (embed/extract/capacity), `lsb_analysis` (planes, statistics), `SteganographyAnalyzer` | Implemented (LSB only) |
| `watermarking` | `lsb_watermark` (keyed, redundant LSB watermark) | Implemented. `WatermarkAnalyzer` is still an interface stub; use the functions. |
| `metrics` | `mse`, `psnr`, `ssim` | Implemented |
| `integrity`, `provenance` | `Analyzer` subclasses raising `NotImplementedError` | Interface only |

Pixel-domain algorithms operate on an 8-bit RGB array of shape `(H, W, 3)`. Algorithm descriptions and limitations are in the module docstrings and the README's Technical Methodology section.

## Data flow

1. `POST /api/evidence/upload` validates and hashes the file, then stores the original bytes and an `EvidenceArtifact` in memory.
2. Embedding endpoints decode the original, run an `analysis` function, encode the result as PNG, store it as a derived artifact (`art_…`), compute metrics against the original and append a `ProvenanceRecord` to the evidence.
3. Extraction, verification, analysis and comparison endpoints accept either an evidence ID or an artifact ID.

## Notes

- State lives in `app/services/store.py` and is lost on restart. Replacing it with persistence is a later phase.
- `analysis/` is a top-level package; run the backend from the repository root (`--app-dir backend`) so it is importable.
