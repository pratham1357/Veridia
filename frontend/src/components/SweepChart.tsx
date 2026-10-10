/** Hand-drawn SVG chart for an attack sweep: bit error rate against the attack parameter. */
import { METHOD_LABEL } from "../features/operations";
import type { SweepReport } from "../types/watermark";

const W = 520;
const H = 190;
const PAD = { left: 42, right: 12, top: 12, bottom: 30 };

const SERIES_COLOR: Record<string, string> = {
  spatial_lsb: "#f87171",
  dct: "#4ade80",
  dwt: "#60a5fa",
};

/**
 * One line per method. The y axis is the raw bit error rate (0 = every carrier bit
 * correct, 0.5 = indistinguishable from guessing). Filled dots mark parameter values
 * where the watermark still verified, hollow dots where it did not, so the chart never
 * implies robustness that verification did not confirm.
 */
export default function SweepChart({ report }: { report: SweepReport }) {
  const all = report.series.flatMap((s) => s.rows.map((r) => r.parameter));
  if (all.length === 0) return null;
  const xMin = Math.min(...all);
  const xMax = Math.max(...all);
  const span = xMax - xMin || 1;
  const sx = (x: number) => PAD.left + ((x - xMin) / span) * (W - PAD.left - PAD.right);
  const sy = (y: number) => PAD.top + (1 - Math.min(y, 1) / 1) * (H - PAD.top - PAD.bottom);

  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const xTicks = report.series[0].rows.map((r) => r.parameter);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded bg-slate-950" role="img" aria-label={`${report.attack_label} sweep`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={sy(t)} y2={sy(t)} stroke="#1e293b" strokeWidth={1} />
            <text x={PAD.left - 6} y={sy(t) + 3} textAnchor="end" className="fill-slate-500" style={{ fontSize: 9 }}>{t.toFixed(2)}</text>
          </g>
        ))}
        {/* 0.5 BER = chance level: at or above this the carriers carry no usable signal */}
        <line x1={PAD.left} x2={W - PAD.right} y1={sy(0.5)} y2={sy(0.5)} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />
        <text x={W - PAD.right} y={sy(0.5) - 4} textAnchor="end" className="fill-amber-500" style={{ fontSize: 9 }}>chance level</text>

        {xTicks.map((x) => (
          <text key={x} x={sx(x)} y={H - 10} textAnchor="middle" className="fill-slate-500" style={{ fontSize: 9 }}>{x}</text>
        ))}
        <text x={(W + PAD.left) / 2} y={H - 1} textAnchor="middle" className="fill-slate-500" style={{ fontSize: 9 }}>{report.parameter_label}</text>

        {report.series.map((s) => {
          const pts = s.rows.filter((r) => r.bit_error_rate !== null);
          const color = SERIES_COLOR[s.method] ?? "#94a3b8";
          return (
            <g key={s.method}>
              <polyline
                points={pts.map((r) => `${sx(r.parameter).toFixed(1)},${sy(r.bit_error_rate as number).toFixed(1)}`).join(" ")}
                fill="none"
                stroke={color}
                strokeWidth={1.8}
              />
              {pts.map((r) => (
                <circle
                  key={r.parameter}
                  cx={sx(r.parameter)}
                  cy={sy(r.bit_error_rate as number)}
                  r={3}
                  fill={r.status === "verified" ? color : "#0f172a"}
                  stroke={color}
                  strokeWidth={1.5}
                >
                  <title>{`${METHOD_LABEL[s.method]} · ${report.parameter_label} ${r.parameter} · BER ${(r.bit_error_rate as number).toFixed(3)} · ${r.status}`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-400">
        {report.series.map((s) => (
          <span key={s.method} className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-4 rounded" style={{ background: SERIES_COLOR[s.method] ?? "#94a3b8" }} />
            {METHOD_LABEL[s.method]}
          </span>
        ))}
        <span className="text-slate-500">Filled dot = still verified · hollow = not recovered</span>
      </div>
    </div>
  );
}
