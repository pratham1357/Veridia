# Architecture

## Layers

| Layer | Location | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | Investigator UI. Talks only to the backend API. |
| API | `backend/app/api` | HTTP routing. Thin: validates input and delegates to services. |
| Schemas | `backend/app/schemas` | Pydantic models: `EvidenceArtifact`, `ProvenanceRecord`, request/response models. |
| Services | `backend/app/services` | File-backed store (`store`), ingestion (`evidence_service`), derived artifacts + operation records (`artifacts`), operation catalogue (`operation_registry`), hash-chained timeline and verification (`provenance`), recorded analyses (`investigation`), report export (`reports`), and orchestration per area (`operations`, `watermarking`, `steganalysis`). |
| Storage | `storage/` (git-ignored) | `evidence/<id>/evidence.json`, `images/<image_id>.<ext>`, `reports/<report_id>.{json,html}`. Plain files, no database. |
| Analysis | `analysis/` | Pure algorithms on bytes/NumPy arrays. No web or storage dependencies. |

Frontend types in `frontend/src/types/evidence.ts` mirror the Pydantic schemas; keep them in sync.

## Analysis package

| Package | Contents | Status |
| --- | --- | --- |
| `core` | `sha256_hex`, image decode/encode (`decode_rgb`, `encode_png`, `probe`), `Analyzer` contract, `AnalysisResult`, `Finding`, `EvidenceInput` | Implemented |
| `metadata` | `extract_metadata`, `MetadataAnalyzer` (device, software, timestamp, GPS findings) | Implemented |
| `integrity` | `IntegrityAnalyzer` (hash re-verification, characteristics, compression), `compression` (JPEG tables, IJG quality estimate, blockiness), `ela` (`ELAAnalyzer`, error-level map, block z-scores, clusters), `comparison.compare` (reference vs. subject) | Implemented (ELA experimental) |
| `steganography` | `lsb` (embed/extract/capacity), `lsb_analysis` (planes, LSB statistics, known-cover comparison), `histogram` (channel stats, chi-square attack), `rs_analysis` (RS), `steganalysis` (aggregated report + indicators), `SteganographyAnalyzer` | Implemented (LSB replacement only) |
| `watermarking` | `common` (shared types), `lsb_watermark` (spatial), `dct` (block DCT, YCbCr, DCT visualisation), `dct_watermark` (transform domain), `attacks`, `robustness` (experiment runner) | Implemented. Both schemes expose `embed`, `verify`, `bit_error_rate`, `MAX_MESSAGE_BYTES`, `MIN_COPIES`, so the robustness runner treats them uniformly. `WatermarkAnalyzer(method, key, expected, reference)` wraps verification as an `AnalysisResult`. |
| `metrics` | `mse`, `psnr`, `ssim`, `difference_map`, `difference_statistics`, `channel_statistics`, `channel_histograms` | Implemented |
| `provenance` | `chain` (canonical JSON, `digest`, `entry_hash`, `verify_links` with optional expected head); `ProvenanceAnalyzer` raising `NotImplementedError` | Hash chain implemented; content-based provenance inference not |

All analyzers return the common `AnalysisResult` (status, measurements, findings, interpretation, limitations, data, timestamp); see `analysis/core/base.py`. Pixel-domain algorithms operate on an 8-bit RGB array of shape `(H, W, 3)`. Algorithm descriptions and limitations are in the module docstrings and the README's Technical Methodology section.

## Data flow

1. `POST /api/evidence/upload` validates and hashes the file, writes the original bytes unmodified (write-once, read-only) and the `EvidenceArtifact` to `storage/`, and records the first three chained events.
2. Processing endpoints (embeds and attacks) go through `services/artifacts.derive`, which requires a registered operation name: decode the input image, run an `analysis` function, encode the result as PNG, store it as a derived artifact (`art_…`), compute metrics against the input and append a `ProvenanceRecord` (input image, output image, hashes, safe parameters) to the root evidence.
3. `derive` also appends a `DerivedArtifact` (own ID and hash, parent ID and hash, operation, time) and an `artifact_created` event whose `content_hash` covers both records, then saves `evidence.json`.
4. `POST /api/investigation/{id}/analyses` and `/pipeline` run analyzers on any image belonging to that evidence item, append an `AnalysisRecord` and an `analysis_completed` event, and save. Images from other evidence items are rejected.
5. `POST /api/reports/{id}` verifies the chain, writes the JSON and HTML report files, appends a `ReportRecord` and a `report_exported` event, and saves.
6. `GET /api/provenance/{id}/verify` is read-only: it recomputes the chain, covered records, lineage and every stored file hash.
7. Exploratory endpoints (steganalysis report, watermark verify, compare, ELA map) accept an evidence or artifact ID and are not recorded.

Every mutation of an evidence record happens under the store's lock, and every `record_event` must run *after* the record it covers has been appended, because the event hashes that record.

## Notes

- State lives in `app/services/store.py`, which persists to `storage/` (`VERIDIA_STORAGE_DIR`) and reloads it on startup (FastAPI lifespan). `VERIDIA_PERSIST=false` keeps the old memory-only behaviour; tests use a temporary directory per test.
- Content hashes are computed on records exactly as persisted (`json.loads(model.model_dump_json())`), so a save/reload round trip never changes a hash (e.g. NaN becomes `null` in both).
- New image-producing operations: call `operation_registry.register_operation(OperationSpec(...))` once, then pass the name to `derive`. The frontend reads labels from `GET /api/provenance/operations`.
- `analysis/` is a top-level package; run the backend from the repository root (`--app-dir backend`) so it is importable.
