import type { AnalysisRecord, AnalysisType, WatermarkCheck } from "../types/analysis";
import type { CapacityReport, EvidenceArtifact, OperationResult, ReportRecord, StegoExtractResult } from "../types/evidence";
import type { ChainVerification, OperationInfo } from "../types/provenance";
import type { CoverComparison, SteganalysisReport } from "../types/steganalysis";
import type {
  AttackInfo,
  AttackResult,
  CompareMethodsResult,
  RobustnessReport,
  WatermarkMethod,
  WatermarkVerifyResult,
} from "../types/watermark";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  storage: "persistent" | "memory";
  evidence_count: number;
  storage_load_errors: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep generic message */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const imageUrl = (imageId: string, download = false) =>
  `/api/images/${imageId}${download ? "?download=true" : ""}`;

export const lsbPlaneUrl = (imageId: string, channel: string) => `/api/steganalysis/lsb-plane/${imageId}/${channel}`;
export const dctMapUrl = (imageId: string) => `/api/watermark/dct-map/${imageId}`;
export const differenceUrl = (originalId: string, processedId: string) => `/api/analysis/difference/${originalId}/${processedId}`;
export const elaUrl = (imageId: string, quality: number) => `/api/analysis/ela/${imageId}?quality=${quality}`;
export const reportUrl = (evidenceId: string, reportId: string, format: "json" | "html", download = false) =>
  `/api/reports/${evidenceId}/${reportId}/${format}${download ? "?download=true" : ""}`;

export const getHealth = () => request<HealthResponse>("/api/health");

export const uploadEvidence = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return request<EvidenceArtifact>("/api/evidence/upload", { method: "POST", body: form });
};
export const listEvidence = () => request<EvidenceArtifact[]>("/api/evidence");
export const getEvidence = (id: string) => request<EvidenceArtifact>(`/api/evidence/${id}`);

export const getCapacity = (evidenceId: string) => request<CapacityReport>(`/api/steganography/capacity/${evidenceId}`);
export const embedStego = (evidence_id: string, payload: string) =>
  post<OperationResult>("/api/steganography/embed", { evidence_id, payload });
export const extractStego = (source_id: string) => post<StegoExtractResult>("/api/steganography/extract", { source_id });
export const steganalysisReport = (imageId: string) => request<SteganalysisReport>(`/api/steganalysis/report/${imageId}`);
export const coverComparison = (cover_id: string, suspect_id: string) =>
  post<CoverComparison>("/api/steganalysis/cover-comparison", { cover_id, suspect_id });

export const embedWatermark = (req: {
  evidence_id: string;
  method: WatermarkMethod;
  message: string;
  key: string;
  strength?: number;
}) => post<OperationResult>("/api/watermark/embed", req);
export const verifyWatermark = (req: {
  source_id: string;
  method: WatermarkMethod;
  key: string;
  expected_message: string | null;
  reference_id?: string | null;
}) => post<WatermarkVerifyResult>("/api/watermark/verify", req);
export const listAttacks = () => request<AttackInfo[]>("/api/watermark/attacks");
export const runAttack = (req: {
  image_id: string;
  method: WatermarkMethod;
  attack: string;
  parameter: number;
  message: string;
  key: string;
}) => post<AttackResult>("/api/watermark/attack", req);
export const runRobustness = (req: { image_id: string; method: WatermarkMethod; message: string; key: string }) =>
  post<RobustnessReport>("/api/watermark/robustness", req);
export const compareMethods = (req: { evidence_id: string; message: string; key: string; strength?: number }) =>
  post<CompareMethodsResult>("/api/watermark/compare-methods", req);

export const runAnalysis = (
  evidenceId: string,
  req: { type: AnalysisType; subject_id?: string; reference_id?: string | null; watermark?: WatermarkCheck; ela_quality?: number },
) => post<AnalysisRecord>(`/api/investigation/${evidenceId}/analyses`, req);
export const runPipeline = (
  evidenceId: string,
  req: { subject_id?: string; watermark?: WatermarkCheck | null; include_ela?: boolean; ela_quality?: number },
) => post<AnalysisRecord[]>(`/api/investigation/${evidenceId}/pipeline`, req);

export const getOperations = () => request<OperationInfo[]>("/api/provenance/operations");
export const verifyChain = (evidenceId: string, expectedHead?: string | null) =>
  request<ChainVerification>(
    `/api/provenance/${evidenceId}/verify${expectedHead ? `?expected_head=${encodeURIComponent(expectedHead)}` : ""}`,
  );

export const createReport = (evidenceId: string) => post<ReportRecord>(`/api/reports/${evidenceId}`, {});
export const listReports = (evidenceId: string) => request<ReportRecord[]>(`/api/reports/${evidenceId}`);

export const embedKeyedLSB = (req: {
  evidence_id: string;
  payload: string;
  key: string;
  bits_per_channel: number;
}) => post<OperationResult>("/api/steganography/keyed-lsb/embed", req);

export const extractKeyedLSB = (req: {
  source_id: string;
  key: string;
}) => post<StegoExtractResult>(
  "/api/steganography/keyed-lsb/extract",
  req
);

export const embedLSBMatching = (req: {
  evidence_id: string;
  payload: string;
  seed: number;
}) => post<OperationResult>(
  "/api/steganography/lsb-matching/embed",
  req
);

export const extractLSBMatching = (req: {
  source_id: string;
  payload_bytes: number;
  seed: number;
}) => post<StegoExtractResult>(
  "/api/steganography/lsb-matching/extract",
  req
);
