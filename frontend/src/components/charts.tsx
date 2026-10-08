/** Minimal SVG charts for measured data. No chart library; each chart shows one quantity. */

const W = 400;

export function LineChart({
  points,
  yMin = 0,
  yMax = 1,
  threshold,
  height = 140,
  className = "text-cyan-400",
}: {
  points: { x: number; y: number | null }[];
  yMin?: number;
  yMax?: number;
  threshold?: number;
  height?: number;
  className?: string;
}) {
  const sx = (x: number) => x * W;
  const sy = (y: number) => height - ((y - yMin) / (yMax - yMin)) * height;
  const path = points
    .filter((p) => p.y !== null)
    .map((p) => `${sx(p.x).toFixed(1)},${sy(p.y as number).toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" className={`h-36 w-full rounded bg-slate-950 ${className}`}>
      {threshold !== undefined && (
        <line x1={0} x2={W} y1={sy(threshold)} y2={sy(threshold)} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      )}
      <polyline points={path} fill="none" stroke="currentColor" strokeWidth={2} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

const CHANNEL_COLOR = { red: "#f87171", green: "#4ade80", blue: "#60a5fa", gray: "#cbd5e1" } as const;

export function HistogramChart({ values, channel }: { values: number[]; channel: keyof typeof CHANNEL_COLOR }) {
  const h = 100;
  const max = Math.max(...values, 1);
  const pts = values.map((v, i) => `${((i / 255) * W).toFixed(1)},${(h - (v / max) * h).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${h}`} preserveAspectRatio="none" className="h-24 w-full rounded bg-slate-950">
      <polygon points={`0,${h} ${pts} ${W},${h}`} fill={CHANNEL_COLOR[channel]} fillOpacity={0.35} stroke={CHANNEL_COLOR[channel]} strokeWidth={1} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/** Two histograms of the same channel: reference as an outline, subject filled. */
export function HistogramOverlay({ reference, subject, channel }: { reference: number[]; subject: number[]; channel: keyof typeof CHANNEL_COLOR }) {
  const h = 100;
  const max = Math.max(...reference, ...subject, 1);
  const line = (values: number[]) => values.map((v, i) => `${((i / 255) * W).toFixed(1)},${(h - (v / max) * h).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${h}`} preserveAspectRatio="none" className="h-24 w-full rounded bg-slate-950">
      <polygon points={`0,${h} ${line(subject)} ${W},${h}`} fill={CHANNEL_COLOR[channel]} fillOpacity={0.3} stroke="none" />
      <polyline points={line(reference)} fill="none" stroke="#e2e8f0" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      <polyline points={line(subject)} fill="none" stroke={CHANNEL_COLOR[channel]} strokeWidth={1} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/** Bars of h[2k] - h[2k+1] for each pair of values: LSB replacement drives them towards zero. */
export function PairDifferenceChart({ values, channel }: { values: number[]; channel: keyof typeof CHANNEL_COLOR }) {
  const h = 80;
  const diffs = Array.from({ length: 128 }, (_, k) => values[2 * k] - values[2 * k + 1]);
  const max = Math.max(...diffs.map(Math.abs), 1);
  const bw = W / 128;
  return (
    <svg viewBox={`0 0 ${W} ${h}`} preserveAspectRatio="none" className="h-20 w-full rounded bg-slate-950">
      <line x1={0} x2={W} y1={h / 2} y2={h / 2} stroke="#334155" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      {diffs.map((d, k) => {
        const len = (Math.abs(d) / max) * (h / 2);
        return <rect key={k} x={k * bw} width={bw * 0.8} y={d >= 0 ? h / 2 - len : h / 2} height={len} fill={CHANNEL_COLOR[channel]} />;
      })}
    </svg>
  );
}
