/** Mirrors the common analysis-result structure (backend/app/schemas/evidence.py). Keep in sync. */

export type AnalysisType = "metadata" | "integrity" | "steganalysis" | "watermark" | "comparison";
export type AnalysisStatus = "verified" | "indicator_detected" | "no_indicator" | "inconclusive" | "not_applicable";
export type Measurement = string | number | boolean | null;

export interface Finding {
  finding: string;
  evidence: string;
  interpretation: string;
  limitation: string;
  kind: "observation" | "indicator" | "verification";
}

export interface AnalysisResult {
  analysis_type: AnalysisType;
  analyzer_version: string;
  status: AnalysisStatus;
  interpretation: string;
  measurements: Record<string, Measurement>;
  findings: Finding[];
  limitations: string[];
  data: Record<string, unknown>;
  timestamp: string;
}

export interface AnalysisRecord {
  record_id: string;
  subject_image_id: string;
  subject_sha256: string;
  reference_image_id: string | null;
  result: AnalysisResult;
}

/** Shapes of ``result.data`` for the analyses that carry structured output. */
export interface ChannelStat {
  channel: "red" | "green" | "blue" | "gray";
  mean: number;
  std: number;
  min: number;
  max: number;
}

export type Histograms = Record<ChannelStat["channel"], number[]>;

export interface IntegrityData {
  channels: ChannelStat[];
  histograms: Histograms;
  jpeg: { tables: Record<string, number[]>; subsampling: string; progressive: boolean } | null;
}

export interface ComparisonData {
  difference: { changed_samples_per_channel: Record<"red" | "green" | "blue", number> };
  reference: { channels: ChannelStat[]; histograms: Histograms };
  subject: { channels: ChannelStat[]; histograms: Histograms };
}

export interface WatermarkCheck {
  method: "spatial_lsb" | "dct";
  key: string;
  expected_message: string | null;
}
