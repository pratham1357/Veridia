import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AnalysisResultCard, AnalysisStatusBadge, MeasurementsGrid } from "../components/analysis";
import { ChannelHistograms, ChannelStatsTable } from "../components/channels";
import { ArtifactTree, ChainBadge, Timeline } from "../components/provenance";
import { Button, ErrorText, Hash, inputClass, PageHeader, Panel, RequireEvidence, Toggle } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { formatBytes } from "../features/format";
import ComparisonView from "../features/investigation/ComparisonView";
import ELAView from "../features/investigation/ELAView";
import ImagePicker from "../features/investigation/ImagePicker";
import { ANALYSIS_LABEL, imageName, METHOD_LABEL } from "../features/operations";
import { useRunner } from "../features/useRunner";
import { imageUrl, runAnalysis, runPipeline } from "../services/api";
import type { AnalysisRecord, AnalysisType, IntegrityData, WatermarkCheck } from "../types/analysis";
import type { EvidenceArtifact } from "../types/evidence";

const ORDER: AnalysisType[] = ["metadata", "integrity", "ela", "steganalysis", "watermark", "comparison"];
const ELA_QUALITIES = [75, 85, 90, 95];

function QuantTable({ values }: { values: number[] }) {
  return (
    <div className="inline-grid grid-cols-8 gap-px rounded border border-slate-800 bg-slate-800 font-mono text-[10px]">
      {values.map((v, i) => <span key={i} className="bg-slate-950 px-1.5 py-0.5 text-right text-slate-300">{v}</span>)}
    </div>
  );
}

function Detail({ record, evidence }: { record: AnalysisRecord; evidence: EvidenceArtifact }) {
  const m = record.result.measurements;
  switch (record.result.analysis_type) {
    case "metadata":
      return <MeasurementsGrid measurements={m} only={["make", "model", "software", "datetime_original", "datetime", "gps_present", "exif_status", "exif_entries", "format", "color_mode", "bit_depth", "icc_profile"]} />;
    case "integrity": {
      const data = record.result.data as unknown as IntegrityData;
      return (
        <div className="space-y-4">
          <MeasurementsGrid measurements={m} only={["hash_match", "format", "file_size", "width", "height", "blockiness", "jpeg_quality_estimate", "jpeg_standard_tables", "jpeg_subsampling", "jpeg_progressive"]} />
          {data.jpeg?.tables && (
            <div className="flex flex-wrap gap-6">
              {Object.entries(data.jpeg.tables).map(([id, t]) => (
                <div key={id}>
                  <div className="mb-1 text-xs text-slate-500">Quantization table {id} ({id === "0" ? "luminance" : "chrominance"})</div>
                  <QuantTable values={t} />
                </div>
              ))}
            </div>
          )}
          <ChannelStatsTable stats={data.channels} />
          <ChannelHistograms histograms={data.histograms} />
        </div>
      );
    }
    case "ela":
      return <ELAView record={record} />;
    case "steganalysis":
      return (
        <div>
          <MeasurementsGrid measurements={m} only={["chi_square_p", "chi_square_consistent_prefix", "rs_mean_estimate", "veridia_header_found", "lsb_capacity_bytes", "lsb_ones_red", "lsb_ones_green", "lsb_ones_blue"]} />
          <Link to="/steganalysis" className="mt-2 inline-block text-xs text-cyan-400 underline">Open the full steganalysis view (histograms, chi-square curve, LSB planes)</Link>
        </div>
      );
    case "watermark":
      return <MeasurementsGrid measurements={m} only={["method", "extraction_status", "extracted_message", "bit_agreement", "bit_error_rate", "key_supplied", "reference_psnr_db", "reference_ssim", "param_copies"]} />;
    case "comparison":
      return (
        <ComparisonView
          record={record}
          referenceName={record.reference_image_id ? imageName(evidence, record.reference_image_id) : ""}
          subjectName={imageName(evidence, record.subject_image_id)}
        />
      );
  }
}

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const [subject, setSubject] = useState(evidenceId);
  const [withWatermark, setWithWatermark] = useState(false);
  const [wm, setWm] = useState<WatermarkCheck>({ method: "dct", key: "", expected_message: null });
  const [withEla, setWithEla] = useState(false);
  const [elaQuality, setElaQuality] = useState(90);
  const { busy, error, run } = useRunner();

  useEffect(() => setSubject(evidenceId), [evidenceId]);
  useEffect(() => {
    void refresh(); // pick up artifacts and analyses created on other pages
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const latest = useMemo(() => {
    const out: Partial<Record<AnalysisType, AnalysisRecord>> = {};
    for (const r of evidence?.analyses ?? []) if (r.subject_image_id === subject) out[r.result.analysis_type] = r;
    return out;
  }, [evidence, subject]);

  if (!evidence) return null;
  const isOriginal = subject === evidenceId;
  const watermark = withWatermark ? wm : null;

  const pipeline = () =>
    run(() => runPipeline(evidenceId, { subject_id: subject, watermark, include_ela: withEla, ela_quality: elaQuality }), () => void refresh());
  const single = (type: AnalysisType) =>
    run(
      () => runAnalysis(evidenceId, {
        type,
        subject_id: subject,
        reference_id: type === "comparison" || (type === "watermark" && !isOriginal) ? evidenceId : null,
        ...(type === "watermark" ? { watermark: wm } : {}),
        ...(type === "ela" ? { ela_quality: elaQuality } : {}),
      }),
      () => void refresh(),
    );

  return (
    <>
      <Panel title="Evidence identity">
        <div className="flex flex-col gap-5 md:flex-row">
          <img src={imageUrl(evidenceId)} alt="Evidence" className="max-h-40 rounded border border-slate-800 bg-slate-950 object-contain" />
          <dl className="grid min-w-0 flex-1 grid-cols-[8rem_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-slate-500">Evidence ID</dt><dd className="font-mono text-xs">{evidence.evidence_id}</dd>
            <dt className="text-slate-500">SHA-256</dt><dd><Hash value={evidence.sha256} /></dd>
            <dt className="text-slate-500">File</dt><dd>{evidence.original_filename} · {evidence.file_type.mime_type} · {formatBytes(evidence.file_size)} · {evidence.width}×{evidence.height}</dd>
            <dt className="text-slate-500">Acquired</dt><dd>{new Date(evidence.created_at).toLocaleString()}</dd>
            <dt className="text-slate-500">Record</dt><dd>{evidence.derived_artifacts.length} derived artifact(s) · {evidence.analyses.length} recorded analysis result(s) · {evidence.reports.length} report(s)</dd>
            <dt className="text-slate-500">Integrity</dt>
            <dd className="flex flex-wrap items-center gap-3">
              <ChainBadge evidenceId={evidenceId} refreshKey={evidence.timeline.length} />
              <Link to="/provenance" className="text-xs text-cyan-400 underline">verify</Link>
              <Link to="/reports" className="text-xs text-cyan-400 underline">export report</Link>
            </dd>
          </dl>
        </div>
      </Panel>

      <Panel title="Run analysis">
        <div className="grid gap-4 md:grid-cols-2">
          <ImagePicker evidence={evidence} value={subject} onChange={setSubject} label="Image under investigation" />
          <div className="space-y-3">
            <div>
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input type="checkbox" checked={withEla} onChange={(e) => setWithEla(e.target.checked)} />
                Include error level analysis <span className="rounded bg-amber-500/15 px-1.5 text-[10px] uppercase tracking-wider text-amber-300">experimental</span>
              </label>
              {withEla && (
                <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
                  Recompression quality
                  <Toggle options={ELA_QUALITIES.map((q) => ({ id: String(q), label: `q${q}` }))} value={String(elaQuality)} onChange={(q) => setElaQuality(Number(q))} />
                </div>
              )}
            </div>
            <div>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={withWatermark} onChange={(e) => setWithWatermark(e.target.checked)} />
              Include watermark verification
            </label>
            {withWatermark && (
              <div className="mt-2 space-y-2">
                <Toggle options={(["dct", "spatial_lsb"] as const).map((m) => ({ id: m, label: METHOD_LABEL[m] }))} value={wm.method} onChange={(method) => setWm({ ...wm, method })} />
                <input placeholder="Key (not recorded)" value={wm.key} onChange={(e) => setWm({ ...wm, key: e.target.value })} className={inputClass} />
                <input placeholder="Expected message (optional)" value={wm.expected_message ?? ""} onChange={(e) => setWm({ ...wm, expected_message: e.target.value || null })} className={inputClass} />
              </div>
            )}
            </div>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          The full analysis runs metadata → integrity{withEla ? " → ELA" : ""} → steganalysis{withWatermark ? " → watermark verification" : ""}{isOriginal ? "" : " → comparison with the original"}. Every result is recorded on the evidence and anchored in the hash-chained timeline.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button disabled={busy} onClick={pipeline}>{busy ? "Running…" : "Run full analysis"}</Button>
          {ORDER.filter((t) => t !== "comparison" || !isOriginal).filter((t) => t !== "watermark" || withWatermark).filter((t) => t !== "ela" || withEla).map((t) => (
            <Button key={t} disabled={busy} onClick={() => single(t)} className="bg-slate-700 hover:bg-slate-600">{ANALYSIS_LABEL[t]}</Button>
          ))}
        </div>
        <ErrorText message={error} />
      </Panel>

      <Panel title={`Findings summary: ${imageName(evidence, subject)}`}>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-slate-800">
            {ORDER.map((t) => {
              const r = latest[t];
              return (
                <tr key={t}>
                  <td className="w-44 py-2 pr-4 text-slate-400">{ANALYSIS_LABEL[t]}</td>
                  <td className="w-44 pr-4">{r ? <AnalysisStatusBadge status={r.result.status} /> : <span className="text-xs text-slate-600">not run</span>}</td>
                  <td className="text-xs text-slate-400">{r?.result.interpretation}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-slate-500">
          Each analysis reports measurements, findings and their limitations. VERIDIA does not combine them into an authenticity verdict or score.
        </p>
      </Panel>

      {ORDER.map((t) => latest[t] && (
        <AnalysisResultCard key={t} record={latest[t]!} subjectName={imageName(evidence, subject)}>
          <Detail record={latest[t]!} evidence={evidence} />
        </AnalysisResultCard>
      ))}

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Derived artifacts">
          <ArtifactTree evidence={evidence} />
        </Panel>
        <Panel title="Timeline (most recent)">
          <Timeline events={evidence.timeline} limit={12} />
          <Link to="/provenance" className="mt-3 inline-block text-xs text-cyan-400 underline">Full provenance and timeline</Link>
        </Panel>
      </div>
    </>
  );
}

export default function Investigation() {
  return (
    <section>
      <PageHeader title="Investigation" subtitle="One evidence item through metadata, integrity, steganalysis, watermark verification and comparison" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
