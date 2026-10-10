import { useState } from "react";
import DifferenceImage from "../../components/DifferenceImage";
import { Button, ErrorText, inputClass, Panel } from "../../components/ui";
import { formatBer, RobustnessTable, StatusBadge } from "../../components/watermark";
import { formatPsnr } from "../format";
import { compareMethods } from "../../services/api";
import type { CompareMethodsResult } from "../../types/watermark";
import { useEvidence } from "../evidence/EvidenceContext";
import { METHOD_LABEL, WATERMARK_METHODS } from "../operations";
import { useRunner } from "../useRunner";

export default function CompareMethods({ evidenceId }: { evidenceId: string }) {
  const { refresh } = useEvidence();
  const [message, setMessage] = useState("VERIDIA");
  const [key, setKey] = useState("");
  const [strength, setStrength] = useState(25);
  const [result, setResult] = useState<CompareMethodsResult | null>(null);
  const { busy, error, run } = useRunner();
  const bytes = new TextEncoder().encode(message).length;

  const start = () =>
    run(() => compareMethods({ evidence_id: evidenceId, message, key, strength }), (r) => {
      setResult(r);
      void refresh();
    });

  const byMethod = new Map((result?.methods ?? []).map((m) => [m.method, m]));
  const series = WATERMARK_METHODS.map((m) => byMethod.get(m)).filter((m) => m !== undefined);

  return (
    <>
      <Panel title="Experiment">
        <p className="mb-3 text-sm text-slate-300">
          Embeds the same message with both methods into the active evidence, then measures imperceptibility (MSE, PSNR, SSIM against the original) and runs
          the same attack suite on each result. The results are measurements on this image only; interpret the tradeoffs rather than reading a winner off one number.
        </p>
        <label className="text-xs text-slate-400">Message (1–16 bytes, so it fits both methods)</label>
        <input value={message} onChange={(e) => setMessage(e.target.value)} className={inputClass} />
        <label className="mt-3 block text-xs text-slate-400">Key (optional)</label>
        <input value={key} onChange={(e) => setKey(e.target.value)} className={inputClass} />
        <label className="mt-3 block text-xs text-slate-400">DCT strength: {strength}</label>
        <input type="range" min={5} max={60} value={strength} onChange={(e) => setStrength(Number(e.target.value))} className="w-full max-w-sm" />
        <div>
          <Button className="mt-3" disabled={busy || !message || bytes > 16} onClick={start}>{busy ? "Running…" : "Run comparison"}</Button>
        </div>
        <ErrorText message={error} />
      </Panel>

      {result && series.length > 0 && (
        <>
          <Panel title="Imperceptibility and verification">
            <table className="w-full max-w-3xl text-sm">
              <thead className="text-left text-xs text-slate-500">
                <tr><th className="py-2 pr-4">Measurement</th>{series.map((m) => <th key={m.method} className="pr-4">{METHOD_LABEL[m.method]}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono text-xs">
                <tr><td className="py-1.5 font-sans text-slate-400">MSE</td>{series.map((m) => <td key={m.method}>{m.record.metrics.mse.toFixed(4)}</td>)}</tr>
                <tr><td className="py-1.5 font-sans text-slate-400">PSNR</td>{series.map((m) => <td key={m.method}>{formatPsnr(m.record.metrics.psnr_db)}</td>)}</tr>
                <tr><td className="py-1.5 font-sans text-slate-400">SSIM</td>{series.map((m) => <td key={m.method}>{m.record.metrics.ssim.toFixed(4)}</td>)}</tr>
                <tr><td className="py-1.5 font-sans text-slate-400">Verification (no attack)</td>{series.map((m) => <td key={m.method}><StatusBadge status={m.verification.status} /></td>)}</tr>
                <tr><td className="py-1.5 font-sans text-slate-400">Attacks verified</td>
                  {series.map((m) => {
                    const attacked = m.robustness.filter((r) => r.attack !== "none");
                    return <td key={m.method}>{attacked.filter((r) => r.status === "verified").length} / {attacked.length}</td>;
                  })}
                </tr>
              </tbody>
            </table>
            <div className="mt-4 flex flex-col gap-4 md:flex-row">
              {series.map((m) => <DifferenceImage key={m.method} originalId={result.original.image_id} processedId={m.artifact.image_id} />)}
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Difference images in method order: {series.map((m) => METHOD_LABEL[m.method]).join(", ")}. The DCT footprint shows an 8×8 block structure; the
              wavelet footprint follows edges instead, because its carriers are the directional detail bands.
            </p>
          </Panel>

          <Panel title="Robustness, side by side">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-slate-500">
                  <tr><th className="py-2 pr-4">Attack</th><th className="pr-4">Parameter</th>{series.map((m) => <th key={m.method} className="pr-4">{METHOD_LABEL[m.method]}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {series[0].robustness.map((row, i) => (
                    <tr key={i}>
                      <td className="py-1.5 pr-4">{row.attack_label}</td>
                      <td className="pr-4 font-mono text-xs">{row.attack === "none" ? "—" : `${row.parameter_label} ${row.parameter}`}</td>
                      {series.map((m) => {
                        const cell = m.robustness[i];
                        return (
                          <td key={m.method} className="pr-4">
                            <StatusBadge status={cell.status} /> <span className="ml-1 font-mono text-xs text-slate-500">BER {formatBer(cell.bit_error_rate)}</span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details className="mt-4 text-sm">
              <summary className="cursor-pointer text-xs text-slate-400">Full measurements per method</summary>
              {series.map((m) => (
                <div key={m.method} className="mt-4">
                  <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">{METHOD_LABEL[m.method]}</div>
                  <RobustnessTable rows={m.robustness} />
                </div>
              ))}
            </details>
          </Panel>
        </>
      )}
    </>
  );
}
