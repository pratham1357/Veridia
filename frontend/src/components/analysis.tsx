import type { ReactNode } from "react";
import { ANALYSIS_LABEL, STATUS_LABEL } from "../features/operations";
import type { AnalysisRecord, AnalysisStatus, Finding, Measurement } from "../types/analysis";

const STATUS_STYLE: Record<AnalysisStatus, string> = {
  verified: "bg-emerald-500/15 text-emerald-300",
  indicator_detected: "bg-amber-500/15 text-amber-300",
  no_indicator: "bg-slate-700/60 text-slate-300",
  inconclusive: "bg-violet-500/15 text-violet-300",
  not_applicable: "bg-slate-800 text-slate-500",
};

const KIND_STYLE: Record<Finding["kind"], string> = {
  indicator: "text-amber-300",
  verification: "text-emerald-300",
  observation: "text-slate-400",
};

export function AnalysisStatusBadge({ status }: { status: AnalysisStatus }) {
  return <span className={`whitespace-nowrap rounded px-2 py-0.5 text-xs ${STATUS_STYLE[status]}`}>{STATUS_LABEL[status]}</span>;
}

export function formatMeasurement(value: Measurement): string {
  if (value === null) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
  return value;
}

export function FindingsList({ findings }: { findings: Finding[] }) {
  return (
    <div className="space-y-3">
      {findings.map((f, i) => (
        <div key={i} className="rounded border border-slate-800 bg-slate-950 p-3 text-sm">
          <div className="flex items-baseline justify-between gap-3">
            <div className="font-medium text-slate-100">{f.finding}</div>
            <span className={`text-xs uppercase tracking-wider ${KIND_STYLE[f.kind]}`}>{f.kind}</span>
          </div>
          <dl className="mt-2 grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1 text-xs">
            <dt className="text-slate-500">Evidence</dt><dd className="text-slate-300">{f.evidence}</dd>
            <dt className="text-slate-500">Interpretation</dt><dd className="text-slate-300">{f.interpretation}</dd>
            <dt className="text-slate-500">Limitation</dt><dd className="text-amber-200/80">{f.limitation}</dd>
          </dl>
        </div>
      ))}
    </div>
  );
}

export function MeasurementsGrid({ measurements, only }: { measurements: Record<string, Measurement>; only?: string[] }) {
  const entries = Object.entries(measurements).filter(([k]) => !only || only.includes(k));
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
      {entries.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-slate-800/60 py-1">
          <dt className="text-slate-500">{k.replace(/_/g, " ")}</dt>
          <dd className="truncate text-right font-mono text-slate-300" title={String(v)}>{formatMeasurement(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

/** One recorded analysis: status, interpretation, optional type-specific view, findings, measurements, limitations. */
export function AnalysisResultCard({ record, subjectName, children }: { record: AnalysisRecord; subjectName: string; children?: ReactNode }) {
  const r = record.result;
  return (
    <section className="mb-6 rounded border border-slate-800 bg-slate-900 p-5">
      <header className="mb-3 flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">{ANALYSIS_LABEL[r.analysis_type]}</h2>
        <AnalysisStatusBadge status={r.status} />
        <span className="ml-auto text-xs text-slate-500">
          {subjectName} · {new Date(r.timestamp).toLocaleTimeString()} · v{r.analyzer_version}
        </span>
      </header>
      <p className="mb-4 text-sm text-slate-200">{r.interpretation}</p>
      {children && <div className="mb-4">{children}</div>}
      <FindingsList findings={r.findings} />
      <details className="mt-4">
        <summary className="cursor-pointer text-xs text-slate-400">Measurements</summary>
        <div className="mt-2"><MeasurementsGrid measurements={r.measurements} /></div>
      </details>
      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-slate-400">Limitations of this analysis</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-400">
          {r.limitations.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      </details>
    </section>
  );
}
