# Architecture

## Layers

| Layer | Location | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | Investigator UI. Talks only to the backend API. |
| API | `backend/app/api` | HTTP routing. Thin: validates input and delegates to services. |
| Schemas | `backend/app/schemas` | Pydantic models: `EvidenceArtifact`, `ProvenanceRecord`, request/response models. |
| Services | `backend/app/services` | In-memory store (`store`), ingestion (`evidence_service`), derived-artifact + provenance helper (`artifacts`), and orchestration per area (`operations`, `watermarking`, `steganalysis`). |
| Analysis | `analysis/` | Pure algorithms on bytes/NumPy arrays. No web or storage dependencies. |

Frontend types in `frontend/src/types/evidence.ts` mirror the Pydantic schemas; keep them in sync.

## Analysis package

| Package | Contents | Status |
| --- | --- | --- |
| `core` | `sha256_hex`, image decode/encode (`decode_rgb`, `encode_png`, `probe`), `Analyzer` contract | Implemented |
| `metadata` | `extract_metadata`, `MetadataAnalyzer` | Implemented |
| `steganography` | `lsb` (embed/extract/capacity), `lsb_analysis` (planes, LSB statistics, known-cover comparison), `histogram` (channel stats, chi-square attack), `rs_analysis` (RS), `steganalysis` (aggregated report + indicators), `SteganographyAnalyzer` | Implemented (LSB replacement only) |
| `watermarking` | `common` (shared types), `lsb_watermark` (spatial), `dct` (block DCT, YCbCr, DCT visualisation), `dct_watermark` (transform domain), `attacks`, `robustness` (experiment runner) | Implemented. Both schemes expose `embed`, `verify`, `bit_error_rate`, `MAX_MESSAGE_BYTES`, `MIN_COPIES`, so the robustness runner treats them uniformly. `WatermarkAnalyzer` is still an interface stub. |
| `metrics` | `mse`, `psnr`, `ssim`, `difference_map` | Implemented |
| `integrity`, `provenance` | `Analyzer` subclasses raising `NotImplementedError` | Interface only |

Pixel-domain algorithms operate on an 8-bit RGB array of shape `(H, W, 3)`. Algorithm descriptions and limitations are in the module docstrings and the README's Technical Methodology section.

## Data flow

1. `POST /api/evidence/upload` validates and hashes the file, then stores the original bytes and an `EvidenceArtifact` in memory.
2. Processing endpoints (embeds and attacks) go through `services/artifacts.derive`: decode the input image, run an `analysis` function, encode the result as PNG, store it as a derived artifact (`art_…`), compute metrics against the input and append a `ProvenanceRecord` (input image, output image, hashes, safe parameters) to the root evidence.
3. Extraction, verification, analysis and comparison endpoints accept either an evidence ID or an artifact ID.

## Notes

- State lives in `app/services/store.py` and is lost on restart. Replacing it with persistence is a later phase.
- `analysis/` is a top-level package; run the backend from the repository root (`--app-dir backend`) so it is importable.
