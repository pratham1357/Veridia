import type {
  CapacityReport,
  CompareResult,
  EvidenceArtifact,
  LsbAnalysis,
  OperationResult,
  StegoExtractResult,
  WatermarkVerifyResult,
} from "../types/evidence";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
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

export const lsbPlaneUrl = (imageId: string, channel: string) => `/api/steganography/lsb-plane/${imageId}/${channel}`;

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
export const analyzeLsb = (imageId: string) => request<LsbAnalysis>(`/api/steganography/analyze/${imageId}`);

export const embedWatermark = (evidence_id: string, message: string, key: string) =>
  post<OperationResult>("/api/watermark/embed", { evidence_id, message, key });
export const verifyWatermark = (source_id: string, key: string, expected_message: string | null) =>
  post<WatermarkVerifyResult>("/api/watermark/verify", { source_id, key, expected_message });

export const compareImages = (original_id: string, processed_id: string) =>
  post<CompareResult>("/api/analysis/compare", { original_id, processed_id });
