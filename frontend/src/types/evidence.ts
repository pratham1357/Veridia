/** Mirrors backend/app/schemas/evidence.py and operations.py. Keep in sync. */
import type { AnalysisRecord } from "./analysis";

/** Operation names are open-ended identifiers registered by the backend (GET /api/provenance/operations). */
export type Operation = string;

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
  operation: Operation;
  timestamp: string;
  input_evidence_id: string; // root evidence of the chain
  input_image_id: string; // image actually processed (evidence or artifact)
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
  provenance: ProvenanceRecord[];
  derived_artifacts: DerivedArtifact[];
  analyses: AnalysisRecord[];
  reports: ReportRecord[];
  timeline: TimelineEvent[];
}

export interface DerivedArtifact {
  artifact_id: string;
  parent_image_id: string;
  parent_sha256: string;
  operation: Operation;
  created_at: string;
  filename: string;
  mime_type: string;
  size: number;
  sha256: string;
  width: number;
  height: number;
  provenance_record_id: string;
}

export type EventType =
  | "evidence_acquired"
  | "metadata_extracted"
  | "hash_computed"
  | "artifact_created"
  | "analysis_completed"
  | "report_exported";

/** One link of the timeline's SHA-256 hash chain. */
export interface TimelineEvent {
  sequence: number;
  event_id: string;
  timestamp: string;
  event_type: EventType;
  subject_image_id: string;
  description: string;
  reference_id: string | null;
  content_hash: string | null; // hash of the record the event covers
  previous_hash: string; // hash of the preceding event (64 zeros for the first)
  hash: string;
}

export interface ReportRecord {
  report_id: string;
  created_at: string;
  events_covered: number;
  chain_head: string;
  chain_valid: boolean;
  json_sha256: string;
  json_size: number;
  html_sha256: string;
  html_size: number;
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

export interface CompareResult {
  original: ImageSummary;
  processed: ImageSummary;
  metrics: QualityMetrics;
  hashes_differ: boolean;
}
