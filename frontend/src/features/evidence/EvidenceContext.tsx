import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { getEvidence } from "../../services/api";
import type { EvidenceArtifact } from "../../types/evidence";

interface EvidenceState {
  evidence: EvidenceArtifact | null;
  setEvidence: (e: EvidenceArtifact) => void;
  /** Re-fetch the active evidence (e.g. after a processing step appended provenance). */
  refresh: () => Promise<void>;
}

const Ctx = createContext<EvidenceState | null>(null);

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [evidence, setEvidence] = useState<EvidenceArtifact | null>(null);

  const refresh = useCallback(async () => {
    if (evidence) setEvidence(await getEvidence(evidence.evidence_id));
  }, [evidence]);

  return <Ctx.Provider value={{ evidence, setEvidence, refresh }}>{children}</Ctx.Provider>;
}

export function useEvidence(): EvidenceState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useEvidence must be used within EvidenceProvider");
  return ctx;
}
