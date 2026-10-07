import { formatBytes, formatPsnr } from "../features/format";
import { imageUrl } from "../services/api";
import type { ImageSummary, QualityMetrics } from "../types/evidence";
import { Hash, Panel } from "./ui";

function ImageCard({ label, image }: { label: string; image: ImageSummary }) {
  return (
    <div className="min-w-0 flex-1">
      <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <img src={imageUrl(image.image_id)} alt={label} className="max-h-72 w-full rounded border border-slate-800 bg-slate-950 object-contain" />
      <dl className="mt-3 space-y-1 text-xs text-slate-400">
        <div>{image.filename} · {image.width}×{image.height} · {formatBytes(image.size)}</div>
        <div>SHA-256: <Hash value={image.sha256} /></div>
      </dl>
    </div>
  );
}

export default function ImageComparison({
  original,
  processed,
  metrics,
  processedLabel,
}: {
  original: ImageSummary;
  processed: ImageSummary;
  metrics: QualityMetrics;
  processedLabel: string;
}) {
  const sizeDelta = processed.size - original.size;
  return (
    <Panel title="Original vs processed">
      <div className="flex flex-col gap-4 md:flex-row">
        <ImageCard label="Original" image={original} />
        <ImageCard label={processedLabel} image={processed} />
      </div>

      <table className="mt-5 w-full max-w-2xl text-sm">
        <tbody className="divide-y divide-slate-800">
          <tr><td className="py-2 text-slate-400">MSE</td><td className="font-mono">{metrics.mse.toFixed(6)}</td>
            <td className="pl-4 text-xs text-slate-500">Mean squared pixel difference. Lower means less pixel-level change.</td></tr>
          <tr><td className="py-2 text-slate-400">PSNR</td><td className="font-mono">{formatPsnr(metrics.psnr_db)}</td>
            <td className="pl-4 text-xs text-slate-500">10·log₁₀(255²/MSE). Higher generally means closer to the original.</td></tr>
          <tr><td className="py-2 text-slate-400">SSIM</td><td className="font-mono">{metrics.ssim.toFixed(6)}</td>
            <td className="pl-4 text-xs text-slate-500">Structural similarity, 1.0 = identical (7×7 uniform window, mean over RGB).</td></tr>
          <tr><td className="py-2 text-slate-400">File size</td>
            <td className="font-mono">{formatBytes(original.size)} → {formatBytes(processed.size)}</td>
            <td className="pl-4 text-xs text-slate-500">{sizeDelta >= 0 ? "+" : "−"}{formatBytes(Math.abs(sizeDelta))}. Output is lossless PNG, so size also reflects the format change.</td></tr>
        </tbody>
      </table>
      <p className="mt-4 text-xs text-slate-500">
        {original.sha256 === processed.sha256
          ? "The two files are byte-identical (same SHA-256)."
          : "The SHA-256 values differ: any modification, however visually imperceptible, necessarily changes the cryptographic hash."}{" "}
        These metrics are measurements, not a judgement of quality.
      </p>
    </Panel>
  );
}
