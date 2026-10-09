import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AnalysisStatusBadge } from "../components/analysis";
import { ChainVerifier, EVENT_LABEL, HashChip, ProvenanceGraph, Timeline } from "../components/provenance";
import { Hash, PageHeader, Panel, RequireEvidence, Toggle } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { formatBytes, formatPsnr } from "../features/format";
import { ANALYSIS_LABEL, imageName } from "../features/operations";
import { useOperations } from "../features/provenance/OperationsContext";
import { imageUrl } from "../services/api";
import type { EvidenceArtifact, EventType } from "../types/evidence";
import type { ChainVerification } from "../types/provenance";

type Filter = "all" | EventType;

/** Details of one image in the graph: identity, lineage, the operation that produced it, analyses run on it. */
function NodeDetail({ evidence, imageId }: { evidence: EvidenceArtifact; imageId: string }) {
  const { info } = useOperations();
  const artifact = evidence.derived_artifacts.find((a) => a.artifact_id === imageId);
  const record = artifact && evidence.provenance.find((r) => r.record_id === artifact.provenance_record_id);
  const analyses = evidence.analyses.filter((a) => a.subject_image_id === imageId);
  const op = artifact ? info(artifact.operation) : null;
  const sha = artifact?.sha256 ?? evidence.sha256;

  return (
    <div className="mt-4 grid gap-5 rounded border border-slate-800 bg-slate-950 p-4 md:grid-cols-[10rem_1fr]">
      <img src={imageUrl(imageId)} alt="" className="max-h-40 w-full rounded border border-slate-800 bg-slate-900 object-contain" />
      <div className="min-w-0 space-y-3 text-sm">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500">{op ? op.output_label : "Original evidence"}</div>
          <div className="text-slate-100">{imageName(evidence, imageId)}</div>
        </div>
        <dl className="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1 text-xs">
          <dt className="text-slate-500">Image ID</dt><dd className="break-all font-mono text-slate-400">{imageId}</dd>
          <dt className="text-slate-500">SHA-256</dt><dd><Hash value={sha} /></dd>
          {artifact && op && record ? (
            <>
              <dt className="text-slate-500">Derived from</dt>
              <dd className="text-slate-300">{imageName(evidence, artifact.parent_image_id)} · <HashChip value={artifact.parent_sha256} /></dd>
              <dt className="text-slate-500">Operation</dt>
              <dd className="text-slate-300">
                {op.label} <span className="text-slate-500">({op.category}{op.registered ? "" : ", unregistered"})</span>
              </dd>
              <dt className="text-slate-500">Parameters</dt><dd className="break-all font-mono text-slate-400">{JSON.stringify(record.parameters)}</dd>
              <dt className="text-slate-500">vs parent</dt>
              <dd className="font-mono text-slate-400">MSE {record.metrics.mse.toFixed(4)} · PSNR {formatPsnr(record.metrics.psnr_db)} · SSIM {record.metrics.ssim.toFixed(4)}</dd>
              <dt className="text-slate-500">Size</dt><dd className="text-slate-400">{formatBytes(artifact.size)} · {artifact.width}×{artifact.height}</dd>
            </>
          ) : (
            <>
              <dt className="text-slate-500">Acquired</dt><dd className="text-slate-400">{new Date(evidence.created_at).toLocaleString()}</dd>
              <dt className="text-slate-500">Size</dt><dd className="text-slate-400">{formatBytes(evidence.file_size)} · {evidence.width}×{evidence.height}</dd>
            </>
          )}
        </dl>
        <div>
          <div className="mb-1 text-xs text-slate-500">Recorded analyses on this image ({analyses.length})</div>
          {analyses.length === 0 ? (
            <p className="text-xs text-slate-500">None. <Link to="/investigation" className="text-cyan-400 underline">Run an investigation</Link>.</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {analyses.map((a) => (
                <li key={a.record_id} className="flex items-center gap-2 rounded bg-slate-900 px-2 py-1 text-xs text-slate-300">
                  {ANALYSIS_LABEL[a.result.analysis_type]} <AnalysisStatusBadge status={a.result.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function Chain({ evidenceId }: { evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const { label, info } = useOperations();
  const [selected, setSelected] = useState<string>(evidenceId);
  const [filter, setFilter] = useState<Filter>("all");
  const [verification, setVerification] = useState<ChainVerification | null>(null);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => setSelected(evidenceId), [evidenceId]);
  const onResult = useCallback((v: ChainVerification) => setVerification(v), []);

  const invalid = useMemo(() => new Set((verification?.issues ?? []).flatMap((i) => (i.sequence === null ? [] : [i.sequence]))), [verification]);
  const failedFiles = useMemo(() => new Set((verification?.files ?? []).filter((f) => f.status !== "match").map((f) => f.file_id)), [verification]);

  if (!evidence) return null;
  const counts = evidence.timeline.reduce<Partial<Record<EventType, number>>>((acc, e) => ({ ...acc, [e.event_type]: (acc[e.event_type] ?? 0) + 1 }), {});
  const events = filter === "all" ? evidence.timeline : evidence.timeline.filter((e) => e.event_type === filter);
  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: `All (${evidence.timeline.length})` },
    ...(Object.keys(EVENT_LABEL) as EventType[]).filter((t) => counts[t]).map((t) => ({ id: t, label: `${EVENT_LABEL[t]} (${counts[t]})` })),
  ];

  return (
    <>
      <Panel title="Record integrity">
        <ChainVerifier evidenceId={evidenceId} refreshKey={evidence.timeline.length} onResult={onResult} />
      </Panel>

      <Panel title={`Provenance graph · ${evidence.derived_artifacts.length} derived artifact(s)`}>
        <ProvenanceGraph evidence={evidence} selected={selected} onSelect={setSelected} failed={failedFiles} />
        <p className="mt-2 text-xs text-slate-500">
          Each derived image has its own ID and SHA-256 and links to the exact parent it was produced from. The original is never overwritten. Select a node for details.
        </p>
        <NodeDetail evidence={evidence} imageId={selected} />
      </Panel>

      <Panel title="Timeline (hash-chained)">
        <div className="mb-4"><Toggle options={filters} value={filter} onChange={setFilter} /></div>
        <Timeline events={events} showHashes invalid={invalid} />
        <p className="mt-3 text-xs text-slate-500">
          Each event's hash covers its predecessor's hash and the hash of the record it describes, so editing, removing or reordering anything breaks the chain from
          that point on. Exploratory views (e.g. the Steganalysis page) are not recorded; analyses run from Investigation or Comparison are.
        </p>
      </Panel>

      <Panel title="Image-producing operations">
        {evidence.provenance.length === 0 && <p className="text-sm text-slate-400">None yet.</p>}
        <div className="space-y-3">
          {evidence.provenance.map((r) => (
            <div key={r.record_id} className="rounded border border-slate-800 bg-slate-950 p-3">
              <div className="flex flex-wrap items-baseline gap-x-3 text-sm text-slate-200">
                {label(r.operation)}
                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-slate-400">{info(r.operation).category}</span>
                <span className="text-xs text-slate-500">{new Date(r.timestamp).toLocaleString()}</span>
              </div>
              <dl className="mt-2 space-y-1 text-xs text-slate-400">
                <div>Input: {imageName(evidence, r.input_image_id)} · <HashChip value={r.input_sha256} /></div>
                <div>Output: {imageName(evidence, r.output_image_id)} · <HashChip value={r.output_sha256} /></div>
                <div className="break-all">Parameters: <span className="font-mono">{JSON.stringify(r.parameters)}</span></div>
                <div>MSE {r.metrics.mse.toFixed(6)} · PSNR {formatPsnr(r.metrics.psnr_db)} · SSIM {r.metrics.ssim.toFixed(6)} (output vs input)</div>
              </dl>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">Payloads, watermark messages and keys are never recorded.</p>
      </Panel>

      <Panel title="Recorded analyses">
        {evidence.analyses.length === 0 ? (
          <p className="text-sm text-slate-400">None yet. Run analyses from the Investigation page.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-500">
                <tr><th className="py-2 pr-4">Time</th><th className="pr-4">Analysis</th><th className="pr-4">Image</th><th>Status</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {evidence.analyses.map((a) => (
                  <tr key={a.record_id}>
                    <td className="py-1.5 pr-4 font-mono text-xs text-slate-500">{new Date(a.result.timestamp).toLocaleTimeString()}</td>
                    <td className="pr-4">{ANALYSIS_LABEL[a.result.analysis_type]}</td>
                    <td className="pr-4 text-xs text-slate-400">
                      {imageName(evidence, a.subject_image_id)}
                      {a.reference_image_id && <span className="text-slate-600"> vs {imageName(evidence, a.reference_image_id)}</span>}
                    </td>
                    <td><AnalysisStatusBadge status={a.result.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-xs text-slate-500">
          Export everything above as a report on the <Link to="/reports" className="text-cyan-400 underline">Reports</Link> page.
        </p>
      </Panel>
    </>
  );
}

export default function Provenance() {
  return (
    <section>
      <PageHeader title="Provenance" subtitle="What happened, to which image, when, by which operation, producing what result, and whether the record is intact" />
      <RequireEvidence>{(id) => <Chain evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
