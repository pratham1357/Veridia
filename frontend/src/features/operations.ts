import type { AnalysisStatus, AnalysisType } from "../types/analysis";
import type { EvidenceArtifact, Operation } from "../types/evidence";
import type { WatermarkMethod } from "../types/watermark";

export const OPERATION_LABEL: Record<Operation, string> = {
  lsb_steganography_embed: "LSB steganography embed",
  
  keyed_lsb_steganography_embed: "Keyed LSB steganography embed",
  lsb_matching_steganography_embed: "LSB Matching embed",
  watermark_embed: "Spatial (LSB) watermark embed",
  dct_watermark_embed: "DCT watermark embed",
  attack: "Attack (robustness experiment)",
};

export const OUTPUT_LABEL: Record<Operation, string> = {
  lsb_steganography_embed: "Stego image",
    
  keyed_lsb_steganography_embed: "Keyed LSB steganography embed",
  lsb_matching_steganography_embed: "LSB Matching embed",

  watermark_embed: "Spatial-watermarked image",
  dct_watermark_embed: "DCT-watermarked image",
  attack: "Attacked image",
};

export const METHOD_LABEL: Record<WatermarkMethod, string> = {
  spatial_lsb: "Spatial domain (LSB)",
  dct: "Transform domain (DCT)",
};

export const ANALYSIS_LABEL: Record<AnalysisType, string> = {
  metadata: "Metadata",
  integrity: "Integrity",
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

/** All images of an evidence item (original first, then derived artifacts in creation order). */
export function evidenceImages(evidence: EvidenceArtifact): { id: string; label: string; sha256: string }[] {
  return [
    { id: evidence.evidence_id, label: `Original evidence: ${evidence.original_filename}`, sha256: evidence.sha256 },
    ...evidence.derived_artifacts.map((a) => ({ id: a.artifact_id, label: `${OUTPUT_LABEL[a.operation]}: ${a.filename}`, sha256: a.sha256 })),
  ];
}

export function imageName(evidence: EvidenceArtifact, imageId: string): string {
  if (imageId === evidence.evidence_id) return `original (${evidence.original_filename})`;
  return evidence.derived_artifacts.find((a) => a.artifact_id === imageId)?.filename ?? imageId;
}

export const MAX_MESSAGE_BYTES: Record<WatermarkMethod, number> = { spatial_lsb: 64, dct: 16 };
