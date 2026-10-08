import type { ChannelStat, Histograms } from "../types/analysis";
import { HistogramChart, HistogramOverlay } from "./charts";

const ORDER = ["red", "green", "blue", "gray"] as const;

/** Mean / std / min / max per channel; with ``compare`` set, shows reference and subject rows. */
export function ChannelStatsTable({ stats, compare }: { stats: ChannelStat[]; compare?: ChannelStat[] }) {
  const byChannel = (list: ChannelStat[]) => Object.fromEntries(list.map((s) => [s.channel, s]));
  const a = byChannel(stats);
  const b = compare ? byChannel(compare) : null;
  return (
    <table className="w-full max-w-2xl text-xs">
      <thead className="text-left text-slate-500">
        <tr><th className="py-1 pr-4">Channel</th>{b && <th className="pr-4">Image</th>}<th className="pr-4 text-right">Mean</th><th className="pr-4 text-right">Std</th><th className="pr-4 text-right">Min</th><th className="text-right">Max</th></tr>
      </thead>
      <tbody className="divide-y divide-slate-800 font-mono">
        {ORDER.flatMap((ch) =>
          (b ? [["reference", a[ch]], ["subject", b[ch]]] : [["", a[ch]]]).map(([label, s], i) => {
            const stat = s as ChannelStat;
            return (
              <tr key={`${ch}-${i}`}>
                <td className="py-1 pr-4 font-sans capitalize text-slate-400">{i === 0 ? ch : ""}</td>
                {b && <td className="pr-4 font-sans text-slate-500">{label as string}</td>}
                <td className="pr-4 text-right">{stat.mean.toFixed(3)}</td>
                <td className="pr-4 text-right">{stat.std.toFixed(3)}</td>
                <td className="pr-4 text-right">{stat.min}</td>
                <td className="text-right">{stat.max}</td>
              </tr>
            );
          }),
        )}
      </tbody>
    </table>
  );
}

export function ChannelHistograms({ histograms, compare }: { histograms: Histograms; compare?: Histograms }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {ORDER.map((ch) => (
        <div key={ch}>
          <div className="mb-1 text-xs capitalize text-slate-400">{ch}</div>
          {compare ? <HistogramOverlay reference={histograms[ch]} subject={compare[ch]} channel={ch} /> : <HistogramChart values={histograms[ch]} channel={ch} />}
        </div>
      ))}
    </div>
  );
}
