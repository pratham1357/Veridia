# Security Principles

Uploaded files are untrusted input and may be malformed or malicious. Status below reflects Phase 2.

| Principle | Requirement | Status |
| --- | --- | --- |
| File signature validation | Identify type from magic bytes; never trust the client `Content-Type`. | Implemented (PNG, JPEG, BMP) |
| File type validation | Allow-list of formats; extension must match content; full decode must succeed. | Implemented |
| File size limits | Max 10 MB and 8 megapixels (`VERIDIA_MAX_UPLOAD_BYTES`, `VERIDIA_MAX_PIXELS`). | Implemented. The upload is fully received by the framework before the check; streaming enforcement is not done yet. |
| Sanitized filenames | The original name is display metadata only. | Implemented |
| Path traversal prevention | Server-generated IDs; user input never forms a storage path. | Implemented (nothing is written to disk yet) |
| Safe temporary storage | Isolated directory, restrictive permissions, cleanup. | Not applicable yet (in-memory); required when persistence is added |
| No execution | Uploaded files are parsed only as image data. Images are served as their image type with `X-Content-Type-Options: nosniff`. | Implemented |
| Cryptographic hashing | SHA-256 at intake and for every derived file. | Implemented |
| Preservation of originals | Original bytes are stored unmodified; processing produces new artifacts. | Implemented (in memory) |
| Sensitive parameters | Payloads, watermark messages and keys are not written to provenance records. | Implemented |
| Parser hardening | Pillow processes untrusted data; keep it updated and bound resource use. | Partial (pixel limit; no timeouts) |
| Authentication, rate limiting, persistence | — | Not implemented |
