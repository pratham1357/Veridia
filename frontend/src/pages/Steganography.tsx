import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import ImageComparison from "../components/ImageComparison";
import { Button, ErrorText, inputClass, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { evidenceSummary } from "../features/evidence/summary";
import { embedStego, extractStego, getCapacity, imageUrl } from "../services/api";
import type { CapacityReport, OperationResult, StegoExtractResult } from "../types/evidence";

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const [payload, setPayload] = useState("");
  const [capacity, setCapacity] = useState<CapacityReport | null>(null);
  const [result, setResult] = useState<OperationResult | null>(null);
  const [extracted, setExtracted] = useState<StegoExtractResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(null);
    setExtracted(null);
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

      <Panel title="Steganalysis">
        <p className="text-sm text-slate-400">
          LSB planes, channel statistics, histograms, chi-square and RS analysis are on the{" "}
          <Link to="/steganalysis" className="text-cyan-400 underline">Steganalysis</Link> page. Select the generated stego image there as the suspected image
          to see how embedding changes the measurements.
        </p>
      </Panel>
    </>
  );
}

export default function Steganography() {
  return (
    <section>
      <PageHeader title="Steganography" subtitle="LSB embedding and extraction" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
