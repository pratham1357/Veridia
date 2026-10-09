# Security Principles

Uploaded files are untrusted input and may be malformed or malicious. Status below reflects Phase 5.

| Principle | Requirement | Status |
| --- | --- | --- |
| File signature validation | Identify type from magic bytes; never trust the client `Content-Type`. | Implemented (PNG, JPEG, BMP) |
| File type validation | Allow-list of formats; extension must match content; full decode must succeed. | Implemented |
| File size limits | Max 10 MB and 8 megapixels (`VERIDIA_MAX_UPLOAD_BYTES`, `VERIDIA_MAX_PIXELS`). | Implemented. The upload is fully received by the framework before the check; streaming enforcement is not done yet. |
| Sanitized filenames | The original name is display metadata only. | Implemented |
| Path traversal prevention | Server-generated IDs; user input never forms a storage path. | Implemented: every path component is an ID matching `^(ev\|art\|rep)_[0-9a-f]{32}$`; anything else under `storage/` is ignored on load |
| Safe storage | Isolated directory, restrictive permissions, no partial writes. | Implemented: directories 0700; image and report files write-once (`O_EXCL`) then 0400; `evidence.json` 0600, replaced atomically (temp + fsync + rename) |
| No execution | Uploaded files are parsed only as image data. Images are served as their image type with `X-Content-Type-Options: nosniff`. | Implemented |
| Cryptographic hashing | SHA-256 at intake and for every derived file. | Implemented |
| Preservation of originals | Original bytes are stored unmodified; processing produces new artifacts. | Implemented (on disk, read-only) |
| Tamper evidence | Changes to records or files are detectable. | Implemented: SHA-256 hash-chained timeline with content hashes, lineage and file re-hashing (`GET /api/provenance/{id}/verify`). Not tamper-proof: a full rewrite or truncation needs an externally recorded head hash to detect; heads are not signed |
| Report rendering | Recorded strings (filenames, EXIF values, descriptions) are untrusted. | Implemented: every value is HTML-escaped; reports load no scripts or remote resources and are served with `Content-Security-Policy: default-src 'none'` (inline styles and data: images only) and `nosniff`; the UI previews them in a sandboxed iframe |
| Sensitive parameters | Payloads, watermark messages and keys are not written to provenance records. | Implemented |
| Parser hardening | Pillow processes untrusted data; keep it updated and bound resource use. | Partial (pixel limit; no timeouts) |
| Authentication, rate limiting | — | Not implemented. Anyone who can reach the API can read and add evidence |
