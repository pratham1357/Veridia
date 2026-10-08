import { useEffect, useState } from "react";
import { HistogramChart, LineChart, PairDifferenceChart } from "../components/charts";
import DifferenceImage from "../components/DifferenceImage";
import { ErrorText, inputClass, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { OUTPUT_LABEL } from "../features/operations";
import { coverComparison, lsbPlaneUrl, steganalysisReport } from "../services/api";
import type { CoverComparison, SteganalysisReport } from "../types/steganalysis";

const fmt = (v: number | null, digits = 4) => (v === null ? "—" : v.toFixed(digits));

function Report({ report }: { report: SteganalysisReport }) {
  const chi = report.chi_square;
  return (
    <>
      <Panel title="Potential indicators">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
          {report.indicators.map((t, i) => <li key={i}>{t}</li>)}
        </ul>
        <p className="mt-3 rounded border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200">{report.disclaimer}</p>
      </Panel>

      <Panel title="Channel statistics">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-2 pr-4">Channel</th><th className="pr-4">Mean</th><th className="pr-4">Std</th><th className="pr-4">Entropy (bits)</th>
                <th className="pr-4">LSB ones</th><th className="pr-4">LSB transitions</th><th className="pr-4">χ² p</th><th>RS estimate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 font-mono text-xs">
              {report.channels.map((c) => (
                <tr key={c.channel}>
                  <td className="py-1.5 pr-4 font-sans capitalize">{c.channel}</td>
                  <td className="pr-4">{c.mean.toFixed(2)}</td>
                  <td className="pr-4">{c.std.toFixed(2)}</td>
                  <td className="pr-4">{c.entropy_bits.toFixed(3)}</td>
                  <td className="pr-4">{c.ones_ratio.toFixed(4)}</td>
                  <td className="pr-4">{c.transition_ratio.toFixed(4)}</td>
                  <td className="pr-4">{fmt(c.chi_square_p)}</td>
                  <td>{c.rs.estimate === null ? "undefined" : `${(c.rs.estimate * 100).toFixed(1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          LSB ones: fraction of LSBs equal to 1. Transitions: fraction of horizontally adjacent LSBs that differ (≈0.5 for random bits). Maximum LSB capacity:{" "}
          {report.lsb_capacity_bytes.toLocaleString()} bytes.
        </p>
      </Panel>

      <Panel title="Chi-square attack (pairs of values)">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="text-sm">
            <p className="text-slate-300">
              LSB replacement only moves a value within its pair (2k, 2k+1), so embedding random bits pushes the two counts towards equality. The test asks how
              consistent the observed counts are with equalised pairs: p close to 1 means consistent.
            </p>
            <p className="mt-2 text-xs text-slate-500">
              The test assumes random-looking message bits (encrypted or compressed data). Plain-text payloads have a fixed 0 top bit in every byte, so they often
              do not equalise pairs and can go unflagged here even when RS analysis responds.
            </p>
            <dl className="mt-3 space-y-1 font-mono text-xs text-slate-400">
              <div>χ² = {fmt(chi.chi2, 2)} · df = {chi.degrees_of_freedom}</div>
              <div>p (all samples) = {fmt(chi.p_value)}</div>
              <div>consistent prefix (p &gt; 0.95) = {(chi.consistent_prefix_fraction * 100).toFixed(0)}% of samples (≈ {report.prefix_payload_bytes_upper.toLocaleString()} bytes)</div>
            </dl>
          </div>
          <div>
            <div className="mb-1 text-xs text-slate-500">p-value over growing prefixes of the row-major sample stream (dashed: 0.95)</div>
            <LineChart points={chi.curve.map((p) => ({ x: p.fraction, y: p.p_value }))} threshold={0.95} />
            <div className="mt-1 flex justify-between text-xs text-slate-600"><span>0%</span><span>fraction of image analysed</span><span>100%</span></div>
          </div>
        </div>
      </Panel>

      <Panel title="RS analysis (experimental)">
        <p className="mb-3 text-sm text-slate-300">
          Groups of 4 pixels are classified as Regular or Singular by whether flipping LSBs (mask M) or shifted LSBs (mask −M) makes them noisier. In natural images
          R<sub>M</sub>≈R<sub>−M</sub> and S<sub>M</sub>≈S<sub>−M</sub>; LSB embedding separates them, which yields an estimate of the fraction of samples carrying
          embedded bits. Expect a few percent of bias on clean images; the estimate is undefined when the model has no real solution (common near full embedding).
        </p>
        <table className="w-full max-w-2xl text-sm">
          <thead className="text-left text-xs text-slate-500">
            <tr><th className="py-2 pr-4">Channel</th><th className="pr-4">R_M</th><th className="pr-4">S_M</th><th className="pr-4">R_−M</th><th className="pr-4">S_−M</th><th>Estimate</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800 font-mono text-xs">
            {report.channels.map((c) => (
              <tr key={c.channel}>
                <td className="py-1.5 pr-4 font-sans capitalize">{c.channel}</td>
                <td className="pr-4">{fmt(c.rs.r_m, 3)}</td><td className="pr-4">{fmt(c.rs.s_m, 3)}</td>
                <td className="pr-4">{fmt(c.rs.r_neg_m, 3)}</td><td className="pr-4">{fmt(c.rs.s_neg_m, 3)}</td>
                <td>{c.rs.estimate === null ? "undefined" : `${(c.rs.estimate * 100).toFixed(1)}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-slate-500">
          Mean estimate: {report.rs_mean_estimate === null ? "undefined" : `${(report.rs_mean_estimate * 100).toFixed(1)}%`}
        </p>
      </Panel>

      <Panel title="Histograms">
        <div className="grid gap-6 md:grid-cols-3">
          {(["red", "green", "blue"] as const).map((ch) => (
            <div key={ch}>
              <div className="mb-1 text-xs capitalize text-slate-400">{ch}: value histogram (0–255)</div>
              <HistogramChart values={report.histograms[ch]} channel={ch} />
              <div className="mb-1 mt-3 text-xs text-slate-400">Pair differences h[2k] − h[2k+1]</div>
              <PairDifferenceChart values={report.histograms[ch]} channel={ch} />
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">Pair differences shrink towards zero where LSB replacement has equalised pairs; compare a known cover with the suspected image.</p>
      </Panel>

      <Panel title="LSB planes">
        <div className="grid gap-4 sm:grid-cols-3">
          {(["red", "green", "blue"] as const).map((ch) => (
            <div key={ch}>
              <div className="mb-1 text-xs capitalize text-slate-400">{ch}</div>
              <img src={lsbPlaneUrl(report.image_id, ch)} alt={`${ch} LSB plane`} style={{ imageRendering: "pixelated" }} className="w-full rounded border border-slate-800 bg-black" />
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">White = LSB 1, black = LSB 0. Sequential embedding often shows as a noise-like band starting at the top rows.</p>
      </Panel>
    </>
  );
}

function CoverPanel({ comparison }: { comparison: CoverComparison }) {
  return (
    <Panel title="Known cover vs suspected image (direct measurement)">
      <p className="mb-3 text-sm text-slate-300">
        With the true cover available, changes are measured directly rather than inferred statistically.
      </p>
      <div className="flex flex-col gap-6 md:flex-row">
        <dl className="space-y-1 text-sm">
          <div>Changed samples: <span className="font-mono">{comparison.changed_samples.toLocaleString()} / {comparison.total_samples.toLocaleString()} ({(comparison.changed_fraction * 100).toFixed(3)}%)</span></div>
          <div>Largest change: <span className="font-mono">±{comparison.max_abs_difference}</span> {comparison.lsb_only ? "(LSB-only changes)" : "(changes beyond the LSB)"}</div>
          <div>Per channel: <span className="font-mono">R {comparison.changed_per_channel.red} · G {comparison.changed_per_channel.green} · B {comparison.changed_per_channel.blue}</span></div>
          <div>Changed region (sample index): <span className="font-mono">{comparison.first_changed_index ?? "—"} → {comparison.last_changed_index ?? "—"}</span></div>
        </dl>
        <DifferenceImage originalId={comparison.cover.image_id} processedId={comparison.suspect.image_id} />
      </div>
    </Panel>
  );
}

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence } = useEvidence();
  const [suspectId, setSuspectId] = useState(evidenceId);
  const [useCover, setUseCover] = useState(true);
  const [report, setReport] = useState<SteganalysisReport | null>(null);
  const [comparison, setComparison] = useState<CoverComparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  const records = evidence?.provenance ?? [];
  const isOriginal = suspectId === evidenceId;

  useEffect(() => setSuspectId(evidenceId), [evidenceId]);
  useEffect(() => {
    setReport(null);
    setError(null);
    steganalysisReport(suspectId).then(setReport).catch((e) => setError(e.message));
  }, [suspectId]);
  useEffect(() => {
    setComparison(null);
    if (useCover && !isOriginal) coverComparison(evidenceId, suspectId).then(setComparison).catch((e) => setError(e.message));
  }, [useCover, isOriginal, evidenceId, suspectId]);

  return (
    <>
      <Panel title="Images">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-xs text-slate-400">Suspected image (analysed without assuming anything about its history)</label>
            <select value={suspectId} onChange={(e) => setSuspectId(e.target.value)} className={inputClass}>
              <option value={evidenceId}>Active evidence: {evidence?.original_filename}</option>
              {records.map((r) => (
                <option key={r.record_id} value={r.output_image_id}>
                  {OUTPUT_LABEL[r.operation]} · {new Date(r.timestamp).toLocaleTimeString()} · {r.output_sha256.slice(0, 10)}…
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400">Known cover image</label>
            <label className="mt-2 flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={useCover && !isOriginal} disabled={isOriginal} onChange={(e) => setUseCover(e.target.checked)} />
              Use the active evidence as the known cover
            </label>
            {isOriginal && <p className="mt-1 text-xs text-slate-500">Select a derived image as the suspect to compare against its cover.</p>}
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          To analyse an external image, upload it on the Evidence page; it then becomes the active evidence and can be analysed here without a cover.
        </p>
        <ErrorText message={error} />
      </Panel>
      {comparison && <CoverPanel comparison={comparison} />}
      {report ? <Report report={report} /> : !error && <p className="text-sm text-slate-400">Analysing…</p>}
    </>
  );
}

export default function Steganalysis() {
  return (
    <section>
      <PageHeader title="Steganalysis" subtitle="Interpretable statistical analysis of LSB characteristics: measurements and potential indicators, not verdicts" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
