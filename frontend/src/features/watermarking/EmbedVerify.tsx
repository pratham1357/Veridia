import { useEffect, useState } from "react";
import ImageComparison from "../../components/ImageComparison";
import { Button, ErrorText, inputClass, Panel, Toggle } from "../../components/ui";
import { VerificationResult } from "../../components/watermark";
import { dctMapUrl, embedWatermark, imageUrl, verifyWatermark } from "../../services/api";
import type { OperationResult } from "../../types/evidence";
import type { WatermarkMethod, WatermarkVerifyResult } from "../../types/watermark";
import { useEvidence } from "../evidence/EvidenceContext";
import { evidenceSummary } from "../evidence/summary";
import { MAX_MESSAGE_BYTES } from "../operations";
import { useRunner } from "../useRunner";

const CONCEPT: Record<WatermarkMethod, React.ReactNode> = {
  spatial_lsb: (
    <>
      <strong>Spatial domain:</strong> the message is written directly into pixel values. A short, CRC-protected block is repeated across the
      least significant bits of all RGB samples at key-derived positions. It is simple and cheap and changes each sample by at most 1. It is{" "}
      <strong>fragile</strong>: re-encoding (e.g. JPEG), resizing or noise rewrites the LSBs.
    </>
  ),
  dct: (
    <>
      <strong>Transform domain:</strong> the luminance channel is split into 8×8 blocks and each block is converted with the 2-D DCT (as in
      JPEG). One bit per block is encoded in the <em>relationship</em> between two mid-frequency coefficients, C(4,1) and C(3,2): their
      difference is pushed to at least +strength for a 1 and −strength for a 0. Low frequencies are avoided because changes there are more
      visible, and high frequencies because JPEG discards them first. Extraction is blind: it re-computes the DCT and votes across the
      repeated copies. Higher strength generally means more distortion and more robustness; measure both.
    </>
  ),
};

export default function EmbedVerify({ method, evidenceId }: { method: WatermarkMethod; evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const [message, setMessage] = useState("");
  const [key, setKey] = useState("");
  const [strength, setStrength] = useState(25);
  const [result, setResult] = useState<OperationResult | null>(null);
  const [expected, setExpected] = useState("");
  const [verifyKey, setVerifyKey] = useState("");
  const [target, setTarget] = useState<"watermarked" | "original">("original");
  const [useReference, setUseReference] = useState(true);
  const [verdict, setVerdict] = useState<WatermarkVerifyResult | null>(null);
  const { busy, error, run } = useRunner();

  useEffect(() => {
    setResult(null);
    setVerdict(null);
    setTarget("original");
  }, [evidenceId, method]);

  const maxBytes = MAX_MESSAGE_BYTES[method];
  const messageBytes = new TextEncoder().encode(message).length;

  const embed = () =>
    run(
      () => embedWatermark({ evidence_id: evidenceId, method, message, key, ...(method === "dct" ? { strength } : {}) }),
      (r) => {
        setResult(r);
        setExpected(message);
        setVerifyKey(key);
        setTarget("watermarked");
        setVerdict(null);
        void refresh();
      },
    );

  const verify = () => {
    const onWatermarked = target === "watermarked" && result;
    run(
      () =>
        verifyWatermark({
          source_id: onWatermarked ? result.artifact.image_id : evidenceId,
          method,
          key: verifyKey,
          expected_message: expected || null,
          reference_id: onWatermarked && useReference ? evidenceId : null,
        }),
      setVerdict,
    );
  };

  return (
    <>
      <Panel title="Method">
        <p className="text-sm text-slate-300">{CONCEPT[method]}</p>
      </Panel>

      <Panel title="Embed">
        <label className="text-xs text-slate-400">Watermark message (1–{maxBytes} bytes UTF-8)</label>
        <input value={message} onChange={(e) => setMessage(e.target.value)} className={inputClass} placeholder="e.g. owner:alice" />
        <label className="mt-3 block text-xs text-slate-400">Key (optional; selects the embedding positions)</label>
        <input value={key} onChange={(e) => setKey(e.target.value)} className={inputClass} />
        {method === "dct" && (
          <>
            <label className="mt-3 block text-xs text-slate-400">Strength (minimum coefficient difference): {strength}</label>
            <input type="range" min={5} max={60} value={strength} onChange={(e) => setStrength(Number(e.target.value))} className="w-full max-w-sm" />
          </>
        )}
        <div className="mt-2 text-xs text-slate-400">{messageBytes} / {maxBytes} bytes</div>
        <Button className="mt-3" disabled={busy || !message || messageBytes > maxBytes} onClick={embed}>Embed watermark</Button>
        <ErrorText message={error} />
      </Panel>

      {result && evidence && (
        <>
          <Panel title="Watermarked image">
            <a href={imageUrl(result.artifact.image_id, true)} className="text-sm text-cyan-400 underline">Download {result.artifact.filename}</a>
            <div className="mt-2 font-mono text-xs text-slate-500">{JSON.stringify(result.record.parameters)}</div>
          </Panel>
          <ImageComparison original={evidenceSummary(evidence)} processed={result.artifact} metrics={result.record.metrics} processedLabel="Watermarked" />
          {method === "dct" && (
            <Panel title="DCT-domain view (luminance, 8×8 blocks)">
              <div className="flex flex-col gap-4 md:flex-row">
                {[["Original", evidenceId], ["Watermarked", result.artifact.image_id]].map(([label, id]) => (
                  <div key={id} className="min-w-0 flex-1">
                    <div className="mb-1 text-xs text-slate-500">{label}</div>
                    <img src={dctMapUrl(id)} alt={`${label} DCT magnitudes`} style={{ imageRendering: "pixelated" }} className="max-h-72 w-full rounded border border-slate-800 bg-black object-contain" />
                  </div>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Log-magnitude of each block's DCT coefficients: the DC term sits at each tile's top-left, with frequency increasing right and down. The watermark
                changes only two mid-frequency positions per block, so the views look nearly identical; the difference image above shows the spatial footprint.
              </p>
            </Panel>
          )}
        </>
      )}

      <Panel title="Verify / extract">
        <Toggle
          options={[...(result ? [{ id: "watermarked" as const, label: "Watermarked image" }] : []), { id: "original" as const, label: "Active evidence" }]}
          value={result ? target : "original"}
          onChange={setTarget}
        />
        <label className="mt-3 block text-xs text-slate-400">Key</label>
        <input value={verifyKey} onChange={(e) => setVerifyKey(e.target.value)} className={inputClass} />
        <label className="mt-3 block text-xs text-slate-400">Expected message (optional)</label>
        <input value={expected} onChange={(e) => setExpected(e.target.value)} className={inputClass} />
        {result && target === "watermarked" && (
          <label className="mt-3 flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={useReference} onChange={(e) => setUseReference(e.target.checked)} />
            Compare against the original evidence (extraction itself is blind and does not use it)
          </label>
        )}
        <Button className="mt-3" disabled={busy} onClick={verify}>Verify</Button>
        {verdict && <VerificationResult result={verdict} />}
      </Panel>
    </>
  );
}
