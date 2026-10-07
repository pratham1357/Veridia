import { useEffect, useState } from "react";
import ImageComparison from "../components/ImageComparison";
import { Button, ErrorText, inputClass, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { evidenceSummary } from "../features/evidence/summary";
import { embedWatermark, imageUrl, verifyWatermark } from "../services/api";
import type { OperationResult, WatermarkVerifyResult } from "../types/evidence";

const STATUS_LABEL: Record<WatermarkVerifyResult["status"], { text: string; style: string }> = {
  verified: { text: "Verified: extracted watermark matches the expected message", style: "text-emerald-400" },
  mismatch: { text: "Mismatch: a watermark was extracted but differs from the expected message", style: "text-amber-400" },
  extracted: { text: "Extracted (nothing to compare against)", style: "text-cyan-300" },
  not_found: { text: "No valid watermark found", style: "text-slate-300" },
};

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const [message, setMessage] = useState("");
  const [key, setKey] = useState("");
  const [result, setResult] = useState<OperationResult | null>(null);
  const [expected, setExpected] = useState("");
  const [verifyKey, setVerifyKey] = useState("");
  const [target, setTarget] = useState<"watermarked" | "original">("watermarked");
  const [verdict, setVerdict] = useState<WatermarkVerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(null);
    setVerdict(null);
  }, [evidenceId]);

  const messageBytes = new TextEncoder().encode(message).length;

  async function embed() {
    setError(null);
    try {
      const r = await embedWatermark(evidenceId, message, key);
      setResult(r);
      setExpected(message);
      setVerifyKey(key);
      setTarget("watermarked");
      setVerdict(null);
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  }

  async function verify() {
    setError(null);
    const source = target === "watermarked" && result ? result.artifact.image_id : evidenceId;
    try {
      setVerdict(await verifyWatermark(source, verifyKey, expected || null));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  }

  return (
    <>
      <Panel title="Concept">
        <p className="text-sm text-slate-300">
          <strong>Digital watermarking associates information with media</strong> (ownership, authentication, integrity, provenance); the message does not need to be secret. Contrast with <em>Steganography</em>, which conceals a communication. This module embeds a short, CRC-protected message repeatedly across the whole image at key-derived pseudo-random positions in the LSB plane. It is a <strong>fragile</strong> watermark: JPEG compression, resizing or cropping will destroy it, and with an empty key it is not secret.
        </p>
      </Panel>

      <Panel title="Embed watermark">
        <label className="text-xs text-slate-400">Watermark message (1–64 bytes UTF-8)</label>
        <input value={message} onChange={(e) => setMessage(e.target.value)} className={inputClass} placeholder="e.g. owner:alice" />
        <label className="mt-3 block text-xs text-slate-400">Key (optional; selects the embedding positions)</label>
        <input value={key} onChange={(e) => setKey(e.target.value)} className={inputClass} />
        <div className="mt-2 text-xs text-slate-400">{messageBytes} / 64 bytes</div>
        <Button className="mt-3" disabled={!message || messageBytes > 64} onClick={embed}>Embed watermark</Button>
        <ErrorText message={error} />
      </Panel>

      {result && evidence && (
        <>
          <Panel title="Generated watermarked image">
            <a href={imageUrl(result.artifact.image_id, true)} className="text-sm text-cyan-400 underline">Download {result.artifact.filename}</a>
          </Panel>
          <ImageComparison original={evidenceSummary(evidence)} processed={result.artifact} metrics={result.record.metrics} processedLabel="Watermarked image" />
        </>
      )}

      <Panel title="Verify / extract">
        <div className="mb-3 flex gap-2 text-xs">
          {result && <button onClick={() => setTarget("watermarked")} className={`rounded px-3 py-1 ${target === "watermarked" ? "bg-cyan-500/20 text-cyan-300" : "bg-slate-800 text-slate-400"}`}>Watermarked image</button>}
          <button onClick={() => setTarget("original")} className={`rounded px-3 py-1 ${target === "original" || !result ? "bg-cyan-500/20 text-cyan-300" : "bg-slate-800 text-slate-400"}`}>Active evidence</button>
        </div>
        <label className="text-xs text-slate-400">Key</label>
        <input value={verifyKey} onChange={(e) => setVerifyKey(e.target.value)} className={inputClass} />
        <label className="mt-3 block text-xs text-slate-400">Expected message (optional)</label>
        <input value={expected} onChange={(e) => setExpected(e.target.value)} className={inputClass} />
        <Button className="mt-3" onClick={verify}>Verify</Button>
        {verdict && (
          <div className="mt-3 rounded border border-slate-800 bg-slate-950 p-3 text-sm">
            <div className={STATUS_LABEL[verdict.status].style}>{STATUS_LABEL[verdict.status].text}</div>
            {verdict.message !== null && <div className="mt-1 font-mono">{verdict.message}</div>}
            {verdict.bit_agreement !== null && <div className="mt-1 text-xs text-slate-500">Embedded-bit agreement: {(verdict.bit_agreement * 100).toFixed(2)}%</div>}
            <div className="mt-1 text-xs text-slate-500">{verdict.detail}</div>
          </div>
        )}
      </Panel>
    </>
  );
}

export default function Watermarking() {
  return (
    <section>
      <PageHeader title="Watermarking" subtitle="Embed and verify a keyed spatial-domain watermark" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
