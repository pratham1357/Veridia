/** Mirrors backend/app/schemas/watermark.py. Keep in sync. */
import type { ImageSummary, ProvenanceRecord, QualityMetrics } from "./evidence";

export type WatermarkMethod = "spatial_lsb" | "dct" | "dwt";
export type VerifyStatus = "verified" | "mismatch" | "extracted" | "not_found";

export interface WatermarkVerifyResult {
  method: WatermarkMethod;
  status: VerifyStatus;
  message: string | null;
  bit_agreement: number | null;
  bit_error_rate: number | null;
  parameters: Record<string, string | number>;
  reference_metrics: QualityMetrics | null;
  detail: string;
}

export interface AttackInfo {
  name: string;
  label: string;
  parameter_label: string;
  presets: number[];
  minimum: number;
  maximum: number;
}

export interface RobustnessRow {
  attack: string;
  attack_label: string;
  parameter: number;
  parameter_label: string;
  mse: number;
  psnr_db: number | null;
  ssim: number;
  status: VerifyStatus;
  extracted_message: string | null;
  bit_error_rate: number | null;
}

export interface AttackResult {
  artifact: ImageSummary;
  record: ProvenanceRecord;
  row: RobustnessRow;
}

export interface RobustnessReport {
  image_id: string;
  method: WatermarkMethod;
  rows: RobustnessRow[];
}

export interface MethodComparison {
  method: WatermarkMethod;
  artifact: ImageSummary;
  record: ProvenanceRecord;
  verification: WatermarkVerifyResult;
  robustness: RobustnessRow[];
}

export interface SweepSeries {
  method: WatermarkMethod;
  image_id: string;
  rows: RobustnessRow[];
}

export interface SweepReport {
  attack: string;
  attack_label: string;
  parameter_label: string;
  series: SweepSeries[];
}

export interface CompareMethodsResult {
  original: ImageSummary;
  methods: MethodComparison[];
}
