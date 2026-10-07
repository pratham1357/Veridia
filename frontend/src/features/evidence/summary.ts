import type { EvidenceArtifact, ImageSummary } from "../../types/evidence";

export const evidenceSummary = (e: EvidenceArtifact): ImageSummary => ({
  image_id: e.evidence_id,
  filename: e.original_filename,
  mime_type: e.file_type.mime_type,
  size: e.file_size,
  sha256: e.sha256,
  width: e.width,
  height: e.height,
});
