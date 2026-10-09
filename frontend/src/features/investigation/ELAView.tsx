import { useState } from "react";
import { MeasurementsGrid } from "../../components/analysis";
import { Toggle } from "../../components/ui";
import { elaUrl, imageUrl } from "../../services/api";
import type { AnalysisRecord, ELAData } from "../../types/analysis";

/** Colour for a robust z-score: transparent near the median, warm towards and above the outlier threshold. */
function zColor(z: number, threshold: number): string {
  const t = Math.max(0, Math.min(1, z / (2 * threshold)));
  return `hsla(${Math.round(200 - 170 * t)}, 85%, ${Math.round(55 - 10 * t)}%, ${(0.08 + 0.62 * t).toFixed(2)})`;
}

/** Block z-score grid as SVG, in image pixel coordinates so it overlays the image exactly. */
function BlockOverlay({ data, threshold, showGrid }: { data: ELAData; threshold: number; showGrid: boolean }) {
  const b = data.block_size;
  return (
    <svg viewBox={`0 0 ${data.width} ${data.height}`} preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
      {showGrid &&
        data.block_z.flatMap((row, r) =>
          row.map((z, c) => <rect key={`${r}-${c}`} x={c * b} y={r * b} width={b} height={b} fill={zColor(z, threshold)} />),
        )}
      {data.clusters.map((cl, i) => (
        <rect key={i} x={cl.x} y={cl.y} width={cl.width} height={cl.height} fill="none" stroke="#f87171" strokeWidth={Math.max(1.5, b / 8)} vectorEffect="non-scaling-stroke" />
      ))}
    </svg>
  );
}

export default function ELAView({ record }: { record: AnalysisRecord }) {
  const data = record.result.data as unknown as Partial<ELAData>;
  const threshold = Number(record.result.measurements.z_threshold ?? 6);
  const [mode, setMode] = useState<"overlay" | "map">("overlay");
  const [showGrid, setShowGrid] = useState(true);
  const m = record.result.measurements;

  if (!data.block_z || !data.width || !data.height) {
    return <MeasurementsGrid measurements={m} />;
  }
  const full = data as ELAData;
  const aspect = `${full.width} / ${full.height}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <Toggle options={[{ id: "overlay", label: "Block scores on image" }, { id: "map", label: "Error-level map" }]} value={mode} onChange={setMode} />
        {mode === "overlay" && (
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} /> block shading
          </label>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <figure className="min-w-0">
          <div className="relative w-full overflow-hidden rounded border border-slate-800 bg-slate-950" style={{ aspectRatio: aspect }}>
            {mode === "overlay" ? (
              <>
                <img src={imageUrl(record.subject_image_id)} alt="Analysed image" className="absolute inset-0 h-full w-full object-fill" />
                <BlockOverlay data={full} threshold={threshold} showGrid={showGrid} />
              </>
            ) : (
              <img
                src={elaUrl(record.subject_image_id, full.quality)}
                alt="Error-level map"
                style={{ imageRendering: "pixelated" }}
                className="absolute inset-0 h-full w-full bg-black object-fill"
              />
            )}
          </div>
          <figcaption className="mt-2 text-xs text-slate-500">
            {mode === "overlay"
              ? `Shading: each ${full.block_size} px block's error level relative to the image median (robust z-score). Red outlines: connected blocks above z = ${threshold}.`
              : `|image − JPEG q${full.quality}(image)|, brightness stretched so the largest error is white. Shows where error is high, not how high.`}
          </figcaption>
        </figure>

        <div className="min-w-0 space-y-3">
          <MeasurementsGrid
            measurements={m}
            only={["quality", "block_size", "mean_error", "median_block_error", "max_block_error", "peak_error", "outlier_blocks", "outlier_fraction", "clusters", "largest_cluster_blocks"]}
          />
          {full.clusters.length > 0 && (
            <div>
              <div className="mb-1 text-xs text-slate-500">Outlier clusters (largest first)</div>
              <ul className="space-y-1 font-mono text-xs text-slate-400">
                {full.clusters.slice(0, 6).map((c, i) => (
                  <li key={i}>{c.blocks} block(s) · x {c.x}–{c.x + c.width}, y {c.y}–{c.y + c.height} px</li>
                ))}
                {full.clusters.length > 6 && <li className="text-slate-600">… {full.clusters.length - 6} more</li>}
              </ul>
            </div>
          )}
          <p className="rounded border border-amber-500/30 bg-amber-500/5 p-2 text-xs text-amber-200/80">
            Experimental. Edges, fine texture, noise and saturated colour raise the error level without any manipulation. Compare against what the image shows
            and corroborate with other analyses before reading anything into a highlighted region.
          </p>
        </div>
      </div>
    </div>
  );
}
