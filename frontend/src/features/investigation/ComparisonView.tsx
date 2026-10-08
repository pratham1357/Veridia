import { ChannelHistograms, ChannelStatsTable } from "../../components/channels";
import DifferenceImage from "../../components/DifferenceImage";
import { Hash } from "../../components/ui";
import { formatPsnr } from "../format";
import { imageUrl } from "../../services/api";
import type { AnalysisRecord, ComparisonData } from "../../types/analysis";

/** Side-by-side images, difference map, metrics, histogram overlay and channel statistics for a comparison record. */
export default function ComparisonView({ record, referenceName, subjectName }: { record: AnalysisRecord; referenceName: string; subjectName: string }) {
  const m = record.result.measurements;
  const data = record.result.data as unknown as Partial<ComparisonData>;
  const referenceId = record.reference_image_id;
  if (!referenceId) return null;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 md:flex-row">
        {[["Reference", referenceId, referenceName], ["Subject", record.subject_image_id, subjectName]].map(([label, id, name]) => (
          <div key={label} className="min-w-0 flex-1">
            <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">{label}</div>
            <img src={imageUrl(id)} alt={label} className="max-h-72 w-full rounded border border-slate-800 bg-slate-950 object-contain" />
            <div className="mt-1 truncate text-xs text-slate-400">{name}</div>
          </div>
        ))}
        {record.result.status !== "not_applicable" && <DifferenceImage originalId={referenceId} processedId={record.subject_image_id} />}
      </div>
      <div className="text-xs text-slate-400">Subject SHA-256: <Hash value={record.subject_sha256} /></div>

      {typeof m.mse === "number" && (
        <table className="w-full max-w-2xl text-sm">
          <tbody className="divide-y divide-slate-800">
            <tr><td className="py-1.5 pr-4 text-slate-400">MSE</td><td className="font-mono">{m.mse.toFixed(6)}</td><td className="pl-4 text-xs text-slate-500">Lower = less pixel-level change</td></tr>
            <tr><td className="py-1.5 pr-4 text-slate-400">PSNR</td><td className="font-mono">{formatPsnr(m.psnr_db as number | null)}</td><td className="pl-4 text-xs text-slate-500">Higher = closer to the reference</td></tr>
            <tr><td className="py-1.5 pr-4 text-slate-400">SSIM</td><td className="font-mono">{(m.ssim as number).toFixed(6)}</td><td className="pl-4 text-xs text-slate-500">1.0 = structurally identical</td></tr>
            <tr><td className="py-1.5 pr-4 text-slate-400">Changed pixels</td><td className="font-mono">{(m.changed_pixels as number).toLocaleString()} / {(m.total_pixels as number).toLocaleString()}</td><td className="pl-4 text-xs text-slate-500">{((m.changed_fraction as number) * 100).toFixed(3)}%</td></tr>
            <tr><td className="py-1.5 pr-4 text-slate-400">Max / mean |Δ|</td><td className="font-mono">{m.max_abs_difference as number} / {(m.mean_abs_difference as number).toFixed(4)}</td><td className="pl-4 text-xs text-slate-500">{m.lsb_only ? "All changes are ±1 (LSB level)" : "Changes exceed the LSB"}</td></tr>
          </tbody>
        </table>
      )}

      {data.reference && data.subject && (
        <>
          <div>
            <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">Histogram comparison (outline: reference, filled: subject)</div>
            <ChannelHistograms histograms={data.reference.histograms} compare={data.subject.histograms} />
          </div>
          <div>
            <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">Channel statistics</div>
            <ChannelStatsTable stats={data.reference.channels} compare={data.subject.channels} />
          </div>
        </>
      )}
    </div>
  );
}
