import type { AnalysisStatus, AnalysisType } from "../types/analysis";
import type { EvidenceArtifact, Operation } from "../types/evidence";
import type { OperationInfo } from "../types/provenance";
import type { WatermarkMethod } from "../types/watermark";

export const METHOD_LABEL: Record<WatermarkMethod, string> = {
  spatial_lsb: "Spatial domain (LSB)",
  dct: "Transform domain (DCT)",
};

export const ANALYSIS_LABEL: Record<AnalysisType, string> = {
  metadata: "Metadata",
  integrity: "Integrity",
  ela: "Error level analysis",
  steganalysis: "Steganalysis",
  watermark: "Watermark verification",
  comparison: "Comparison",
};

export const STATUS_LABEL: Record<AnalysisStatus, string> = {
  verified: "Verified",
  indicator_detected: "Indicator detected",
  no_indicator: "No indicator detected",
  inconclusive: "Inconclusive",
  not_applicable: "Not applicable",
};

/** Readable description for an operation name the backend has not (yet) told us about. */
export function fallbackOperation(name: Operation): OperationInfo {
  const readable = name.replace(/_/g, " ");
  return {
    name,
    label: readable.charAt(0).toUpperCase() + readable.slice(1),
    output_label: `Output of ${readable}`,
    category: "unregistered",
    description: "",
    registered: false,
  };
}

/** All images of an evidence item (original first, then derived artifacts in creation order). */
export function evidenceImages(
  evidence: EvidenceArtifact,
  outputLabel: (op: Operation) => string,
): { id: string; label: string; sha256: string }[] {
  return [
    { id: evidence.evidence_id, label: `Original evidence: ${evidence.original_filename}`, sha256: evidence.sha256 },
    ...evidence.derived_artifacts.map((a) => ({ id: a.artifact_id, label: `${outputLabel(a.operation)}: ${a.filename}`, sha256: a.sha256 })),
  ];
}

export function imageName(evidence: EvidenceArtifact, imageId: string): string {
  if (imageId === evidence.evidence_id) return `original (${evidence.original_filename})`;
  return evidence.derived_artifacts.find((a) => a.artifact_id === imageId)?.filename ?? imageId;
}

export const MAX_MESSAGE_BYTES: Record<WatermarkMethod, number> = { spatial_lsb: 64, dct: 16 };
