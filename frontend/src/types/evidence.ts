/** Mirrors backend/app/schemas/evidence.py and operations.py. Keep in sync. */

export interface FindingSet {
  analyzer: string;
  analyzer_version: string;
  indicators: Record<string, unknown>[];
  notes: string[];
}

export type FieldStatus = "available" | "not_available" | "unknown";

export interface MetadataField {
  status: FieldStatus;
  value: string | number | null;
}

export interface ExifEntry {
  ifd: string;
  tag: string;
  value: unknown;
}

export interface ImageMetadata {
  format: MetadataField;
  width: MetadataField;
  height: MetadataField;
  mode: MetadataField;
  bit_depth: MetadataField;
  icc_profile: MetadataField;
  exif: { status: FieldStatus; entries: ExifEntry[] };
}

export interface QualityMetrics {
  mse: number;
  psnr_db: number | null; // null when images are identical
  ssim: number;
}

export interface ImageSummary {
  image_id: string;
  filename: string;
  mime_type: string;
  size: number;
  sha256: string;
  width: number;
  height: number;
}

export interface ProvenanceRecord {
  record_id: string;
  operation: "lsb_steganography_embed" | "watermark_embed";
  timestamp: string;
  input_evidence_id: string;
  input_sha256: string;
  output_image_id: string;
  output_sha256: string;
  parameters: Record<string, string | number | boolean>;
  metrics: QualityMetrics;
}

export interface EvidenceArtifact {
  evidence_id: string;
  original_filename: string;
  file_type: { mime_type: string; extension: string | null };
  file_size: number;
  sha256: string;
  width: number;
  height: number;
  created_at: string; // ISO 8601, UTC
  metadata_results: ImageMetadata | null;
  integrity_results: FindingSet | null;
  steganography_results: FindingSet | null;
  watermark_results: FindingSet | null;
  provenance: ProvenanceRecord[];
}

export interface CapacityReport {
  capacity_bytes: number;
  payload_bytes: number;
  utilization_percent: number;
}

export interface OperationResult {
  artifact: ImageSummary;
  record: ProvenanceRecord;
  capacity: CapacityReport | null;
}

export interface StegoExtractResult {
  found: boolean;
  payload: string | null;
  payload_bytes: number | null;
  detail: string;
}

export interface LsbAnalysis {
  image_id: string;
  channels: { channel: "red" | "green" | "blue"; ones_ratio: number; transition_ratio: number }[];
  veridia_lsb_header_found: boolean;
  note: string;
}

export interface WatermarkVerifyResult {
  status: "verified" | "mismatch" | "extracted" | "not_found";
  message: string | null;
  bit_agreement: number | null;
  detail: string;
}

export interface CompareResult {
  original: ImageSummary;
  processed: ImageSummary;
  metrics: QualityMetrics;
  hashes_differ: boolean;
}
