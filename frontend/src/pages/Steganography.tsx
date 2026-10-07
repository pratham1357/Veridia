import { useEffect, useMemo, useState } from "react";
import ImageComparison from "../components/ImageComparison";
import { Button, ErrorText, inputClass, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { evidenceSummary } from "../features/evidence/summary";
import { analyzeLsb, embedStego, extractStego, getCapacity, imageUrl, lsbPlaneUrl } from "../services/api";
import type { CapacityReport, LsbAnalysis, OperationResult, StegoExtractResult } from "../types/evidence";

function Inspector({ imageId }: { imageId: string }) {
  const [analysis, setAnalysis] = useState<LsbAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAnalysis(null);
    analyzeLsb(imageId).then(setAnalysis).catch((e) => setError(e.message));
  }, [imageId]);

  return (
    <>
      <ErrorText message={error} />
      {analysis && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {analysis.channels.map((c) => (
              <div key={c.channel}>
                <div className="mb-1 text-xs capitalize text-slate-400">{c.channel} LSB plane</div>
                <img src={lsbPlaneUrl(imageId, c.channel)} alt={`${c.channel} LSB plane`} style={{ imageRendering: "pixelated" }} className="w-full rounded border border-slate-800 bg-black" />
                <div className="mt-1 font-mono text-xs text-slate-400">ones {c.ones_ratio.toFixed(4)} · transitions {c.transition_ratio.toFixed(4)}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-sm text-slate-300">
            VERIDIA LSB header at start of stream: <strong>{analysis.veridia_lsb_header_found ? "present" : "not present"}</strong>
          </p>
          <p className="mt-1 text-xs text-slate-500">
            ones = fraction of LSBs equal to 1; transitions = fraction of horizontally adjacent LSBs that differ (≈0.5 for random bits). {analysis.note}
          </p>
        </>
      )}
    </>
  );
}

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const [payload, setPayload] = useState("");
  const [capacity, setCapacity] = useState<CapacityReport | null>(null);
  const [result, setResult] = useState<OperationResult | null>(null);
  const [extracted, setExtracted] = useState<StegoExtractResult | null>(null);
  const [inspect, setInspect] = useState<"original" | "stego">("original");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(null);
    setExtracted(null);
    setInspect("original");
    getCapacity(evidenceId).then(setCapacity).catch((e) => setError(e.message));
  }, [evidenceId]);

  const payloadBytes = useMemo(() => new TextEncoder().encode(payload).length, [payload]);
  const cap = capacity?.capacity_bytes ?? 0;
  const over = payloadBytes > cap;
  const utilization = cap ? (100 * payloadBytes) / cap : 0;

  async function run<T>(fn: () => Promise<T>, then: (v: T) => void) {
    setError(null);
    try {
      then(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  }

  const embed = () =>
    run(() => embedStego(evidenceId, payload), (r) => {
      setResult(r);
      setExtracted(null);
      setInspect("stego");
      void refresh();
    });

  return (
    <>
      <Panel title="Concept">
        <p className="text-sm text-slate-300">
          <strong>Steganography conceals communication</strong>: the goal is that the existence of the message goes unnoticed. This module hides text in the least significant bit of each RGB sample (sequential, unencrypted). Compare with <em>Watermarking</em>, which associates identifying information with media for ownership or authentication.
        </p>
      </Panel>

      <Panel title="Embed payload (LSB)">
        <textarea value={payload} onChange={(e) => setPayload(e.target.value)} rows={3} placeholder="Text payload to hide…" className={inputClass} />
        <div className="mt-2 text-xs text-slate-400">
          Payload {payloadBytes} B · Capacity {capacity ? `${cap} B` : "…"} · Utilization {utilization.toFixed(2)}%
          {over && <span className="ml-2 text-red-400">Payload exceeds capacity.</span>}
        </div>
        <Button className="mt-3" disabled={!payload || over || !capacity} onClick={embed}>Embed</Button>
        <ErrorText message={error} />
      </Panel>

      {result && evidence && (
        <>
          <Panel title="Generated stego image">
            <a href={imageUrl(result.artifact.image_id, true)} className="text-sm text-cyan-400 underline">Download {result.artifact.filename}</a>
            <div className="mt-3 flex gap-3">
              <Button onClick={() => run(() => extractStego(result.artifact.image_id), setExtracted)}>Extract from stego image</Button>
              <Button className="bg-slate-700 hover:bg-slate-600" onClick={() => run(() => extractStego(evidenceId), setExtracted)}>Extract from original</Button>
            </div>
            {extracted && (
              <div className="mt-3 rounded border border-slate-800 bg-slate-950 p-3 text-sm">
                {extracted.found ? <><span className="text-xs text-slate-500">Extracted payload ({extracted.payload_bytes} B)</span><div className="mt-1 whitespace-pre-wrap font-mono">{extracted.payload}</div></> : <span className="text-slate-400">No payload recovered: {extracted.detail}</span>}
              </div>
            )}
          </Panel>
          <ImageComparison original={evidenceSummary(evidence)} processed={result.artifact} metrics={result.record.metrics} processedLabel="Stego image" />
        </>
      )}

      <Panel title="LSB analysis">
        <div className="mb-3 flex gap-2 text-xs">
          <button onClick={() => setInspect("original")} className={`rounded px-3 py-1 ${inspect === "original" ? "bg-cyan-500/20 text-cyan-300" : "bg-slate-800 text-slate-400"}`}>Original</button>
          {result && <button onClick={() => setInspect("stego")} className={`rounded px-3 py-1 ${inspect === "stego" ? "bg-cyan-500/20 text-cyan-300" : "bg-slate-800 text-slate-400"}`}>Stego</button>}
        </div>
        <Inspector imageId={inspect === "stego" && result ? result.artifact.image_id : evidenceId} />
      </Panel>
    </>
  );
}

export default function Steganography() {
  return (
    <section>
      <PageHeader title="Steganography" subtitle="LSB embedding, extraction and LSB-plane inspection" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
