import { formatPsnr } from "../features/format";
import type { RobustnessRow, VerifyStatus, WatermarkVerifyResult } from "../types/watermark";

const STATUS: Record<VerifyStatus, { text: string; style: string }> = {
  verified: { text: "Verified", style: "bg-emerald-500/15 text-emerald-300" },
  mismatch: { text: "Mismatch", style: "bg-amber-500/15 text-amber-300" },
  extracted: { text: "Extracted", style: "bg-cyan-500/15 text-cyan-300" },
  not_found: { text: "Not recovered", style: "bg-slate-700/60 text-slate-300" },
};

export function StatusBadge({ status }: { status: VerifyStatus }) {
  return <span className={`rounded px-2 py-0.5 text-xs ${STATUS[status].style}`}>{STATUS[status].text}</span>;
}

export const formatBer = (v: number | null) => (v === null ? "—" : `${(v * 100).toFixed(2)}%`);

export function VerificationResult({ result }: { result: WatermarkVerifyResult }) {
  return (
    <div className="mt-3 rounded border border-slate-800 bg-slate-950 p-3 text-sm">
      <div className="flex items-center gap-3">
        <StatusBadge status={result.status} />
        {result.message !== null && <span className="font-mono">{result.message}</span>}
      </div>
      <p className="mt-2 text-xs text-slate-500">{result.detail}</p>
      <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1 text-xs text-slate-400 sm:grid-cols-2">
        {result.bit_agreement !== null && <div>Carrier agreement with decoded bits: {(result.bit_agreement * 100).toFixed(2)}%</div>}
        {result.bit_error_rate !== null && <div>Raw bit error rate vs expected: {formatBer(result.bit_error_rate)}</div>}
        {Object.entries(result.parameters).map(([k, v]) => (
          <div key={k}>{k.replace(/_/g, " ")}: <span className="font-mono">{String(v)}</span></div>
        ))}
        {result.reference_metrics && (
          <div className="sm:col-span-2">
            vs. original: MSE {result.reference_metrics.mse.toFixed(4)} · PSNR {formatPsnr(result.reference_metrics.psnr_db)} · SSIM{" "}
            {result.reference_metrics.ssim.toFixed(4)}
          </div>
        )}
      </dl>
    </div>
  );
}

/** Robustness results. PSNR/SSIM measure the attack's distortion relative to the watermarked image. */
export function RobustnessTable({ rows }: { rows: RobustnessRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-slate-500">
          <tr>
            <th className="py-2 pr-4">Attack</th>
            <th className="pr-4">Parameter</th>
            <th className="pr-4 text-right">PSNR</th>
            <th className="pr-4 text-right">SSIM</th>
            <th className="pr-4">Raw BER</th>
            <th>Watermark</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="py-1.5 pr-4">{r.attack_label}</td>
              <td className="pr-4 font-mono text-xs">{r.attack === "none" ? "—" : `${r.parameter_label} ${r.parameter}`}</td>
              <td className="pr-4 text-right font-mono text-xs">{formatPsnr(r.psnr_db)}</td>
              <td className="pr-4 text-right font-mono text-xs">{r.ssim.toFixed(3)}</td>
              <td className="pr-4">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-16 rounded bg-slate-800">
                    <div className="h-1.5 rounded bg-amber-400" style={{ width: `${Math.min(100, (r.bit_error_rate ?? 0) * 200)}%` }} />
                  </div>
                  <span className="font-mono text-xs">{formatBer(r.bit_error_rate)}</span>
                </div>
              </td>
              <td><StatusBadge status={r.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-500">
        PSNR/SSIM measure each attack's distortion relative to the watermarked image. Raw BER is the fraction of individual carrier bits that differ from what was
        embedded, before redundancy voting (bar full at 50%, which is chance level). Decoding can succeed at a non-zero BER because the payload is repeated.
      </p>
    </div>
  );
}
