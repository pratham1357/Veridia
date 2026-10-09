import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChainBadge, ChainVerifier, HashChip } from "../components/provenance";
import { Button, ErrorText, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { formatBytes } from "../features/format";
import { useRunner } from "../features/useRunner";
import { createReport, reportUrl } from "../services/api";
import type { ReportRecord } from "../types/evidence";

function ReportRow({ evidenceId, report, active, onPreview, onCheck }: {
  evidenceId: string;
  report: ReportRecord;
  active: boolean;
  onPreview: () => void;
  onCheck: () => void;
}) {
  return (
    <li className={`rounded border p-3 ${active ? "border-cyan-700 bg-cyan-500/5" : "border-slate-800 bg-slate-950"}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="font-mono text-xs text-slate-300">{report.report_id}</span>
        <span className="text-xs text-slate-500">{new Date(report.created_at).toLocaleString()}</span>
        <span className={`rounded px-2 py-0.5 text-xs ${report.chain_valid ? "bg-emerald-500/15 text-emerald-300" : "bg-red-500/15 text-red-300"}`}>
          {report.chain_valid ? "chain verified at export" : "chain inconsistent at export"}
        </span>
      </div>
      <dl className="mt-2 grid gap-x-4 gap-y-1 text-xs sm:grid-cols-[8rem_1fr]">
        <dt className="text-slate-500">Covers</dt><dd className="text-slate-300">events 0–{report.events_covered - 1}</dd>
        <dt className="text-slate-500">Chain head</dt><dd><HashChip value={report.chain_head} n={20} /></dd>
        <dt className="text-slate-500">JSON</dt><dd className="flex flex-wrap items-center gap-2 text-slate-400"><HashChip value={report.json_sha256} n={16} /> {formatBytes(report.json_size)}</dd>
        <dt className="text-slate-500">HTML</dt><dd className="flex flex-wrap items-center gap-2 text-slate-400"><HashChip value={report.html_sha256} n={16} /> {formatBytes(report.html_size)}</dd>
      </dl>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <button onClick={onPreview} className="rounded bg-slate-800 px-3 py-1 text-slate-200 hover:bg-slate-700">Preview</button>
        <a href={reportUrl(evidenceId, report.report_id, "html")} target="_blank" rel="noreferrer" className="rounded bg-slate-800 px-3 py-1 text-slate-200 hover:bg-slate-700">Open HTML ↗</a>
        <a href={reportUrl(evidenceId, report.report_id, "html", true)} className="rounded bg-slate-800 px-3 py-1 text-slate-200 hover:bg-slate-700">Download HTML</a>
        <a href={reportUrl(evidenceId, report.report_id, "json", true)} className="rounded bg-slate-800 px-3 py-1 text-slate-200 hover:bg-slate-700">Download JSON</a>
        <button onClick={onCheck} className="rounded bg-slate-800 px-3 py-1 text-slate-200 hover:bg-slate-700">Verify record against this head</button>
      </div>
    </li>
  );
}

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const { busy, error, run } = useRunner();
  const [preview, setPreview] = useState<string | null>(null);
  const [checkHead, setCheckHead] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    setPreview(null);
    setCheckHead(null);
  }, [evidenceId]);

  if (!evidence) return null;
  const reports = [...evidence.reports].reverse();
  const generate = () => run(() => createReport(evidenceId), async (r) => {
    await refresh();
    setPreview(r.report_id);
  });

  return (
    <>
      <Panel title="Export">
        <div className="flex flex-wrap items-center gap-3">
          <Button disabled={busy} onClick={generate}>{busy ? "Generating…" : "Generate report"}</Button>
          <ChainBadge evidenceId={evidenceId} refreshKey={evidence.timeline.length} />
        </div>
        <p className="mt-3 max-w-3xl text-xs text-slate-500">
          A report is a snapshot of the record for <span className="text-slate-300">{evidence.original_filename}</span>: identity and metadata, every image with its
          re-checked hash, the provenance chain, {evidence.analyses.length} recorded analysis result(s) with findings and limitations, the hash-chained timeline
          and a chain verification. It is written once as JSON (machine-readable) and HTML (self-contained, printable), and the export is itself recorded in the
          timeline. Reports contain no authenticity verdict. Run analyses first on the <Link to="/investigation" className="text-cyan-400 underline">Investigation</Link> page.
        </p>
        <ErrorText message={error} />
      </Panel>

      <Panel title={`Reports (${reports.length})`}>
        {reports.length === 0 ? (
          <p className="text-sm text-slate-400">No reports exported for this evidence yet.</p>
        ) : (
          <ul className="space-y-3">
            {reports.map((r) => (
              <ReportRow
                key={r.report_id}
                evidenceId={evidenceId}
                report={r}
                active={preview === r.report_id}
                onPreview={() => setPreview(r.report_id)}
                onCheck={() => setCheckHead(r.chain_head)}
              />
            ))}
          </ul>
        )}
      </Panel>

      {checkHead && (
        <Panel title="Verify the current record against a report's head">
          <ChainVerifier key={checkHead} evidenceId={evidenceId} initialHead={checkHead} refreshKey={evidence.timeline.length} />
        </Panel>
      )}

      {preview && (
        <Panel title="Preview">
          <iframe
            title="Report preview"
            src={reportUrl(evidenceId, preview, "html")}
            sandbox=""
            className="h-[75vh] w-full rounded border border-slate-800 bg-white"
          />
          <p className="mt-2 text-xs text-slate-500">Rendered in a sandboxed frame; the report loads no scripts or external resources.</p>
        </Panel>
      )}
    </>
  );
}

export default function Reports() {
  return (
    <section>
      <PageHeader title="Reports" subtitle="Reproducible HTML and JSON investigation reports, anchored in the evidence hash chain" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
