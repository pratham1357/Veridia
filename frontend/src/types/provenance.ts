/** Mirrors backend/app/schemas/provenance.py. Keep in sync. */

export interface OperationInfo {
  name: string;
  label: string;
  output_label: string;
  category: string;
  description: string;
  registered: boolean;
}

export type ChainCheckName = "links" | "event_hashes" | "record_content" | "coverage" | "lineage" | "files" | "head";

export interface ChainCheck {
  name: ChainCheckName;
  label: string;
  passed: boolean;
  detail: string;
}

export interface ChainIssue {
  check: string;
  kind: string;
  detail: string;
  sequence: number | null;
  event_id: string | null;
  record_id: string | null;
}

export interface FileCheck {
  file_id: string;
  kind: "original" | "derived" | "report";
  expected_sha256: string;
  actual_sha256: string | null;
  status: "match" | "mismatch" | "missing";
}

export interface ChainVerification {
  evidence_id: string;
  verified_at: string;
  valid: boolean;
  algorithm: string;
  genesis_hash: string;
  head_hash: string | null;
  event_count: number;
  expected_head: string | null;
  first_invalid_sequence: number | null;
  checks: ChainCheck[];
  issues: ChainIssue[];
  files: FileCheck[];
}
