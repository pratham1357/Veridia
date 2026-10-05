/** Mirrors backend/app/schemas/evidence.py. Keep the two in sync. */

export interface FindingSet {
  analyzer: string;
  analyzer_version: string;
  indicators: Record<string, unknown>[];
  notes: string[];
}

export interface EvidenceArtifact {
  evidence_id: string;
  original_filename: string;
  file_type: { mime_type: string; extension: string | null };
  file_size: number;
  sha256: string;
  created_at: string; // ISO 8601, UTC
  metadata_results: FindingSet | null;
  integrity_results: FindingSet | null;
  steganography_results: FindingSet | null;
  watermark_results: FindingSet | null;
  provenance_results: FindingSet | null;
}
