import { useEffect } from "react";
import { AnalysisStatusBadge } from "../components/analysis";
import { ArtifactTree, Timeline } from "../components/provenance";
import { Hash, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { formatPsnr } from "../features/format";
import { ANALYSIS_LABEL, imageName, OPERATION_LABEL } from "../features/operations";

function Chain() {
  const { evidence, refresh } = useEvidence();
  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  if (!evidence) return null;
  return (
    <>
      <Panel title="Derived artifacts">
        <ArtifactTree evidence={evidence} />
        <p className="mt-3 text-xs text-slate-500">Each artifact has its own ID and SHA-256 and is nested under the image it was derived from. The original is never overwritten.</p>
      </Panel>

      <Panel title="Timeline">
        <Timeline events={evidence.timeline} />
        <p className="mt-3 text-xs text-slate-500">
          Events are written only when the application performs the operation. Exploratory views (e.g. the Steganalysis page) are not recorded; analyses run from
          Investigation or Comparison are.
        </p>
      </Panel>

      <Panel title="Image-producing operations">
        {evidence.provenance.length === 0 && <p className="text-sm text-slate-400">None yet.</p>}
        <div className="space-y-4">
          {evidence.provenance.map((r) => (
            <div key={r.record_id} className="rounded border border-slate-800 bg-slate-950 p-3">
              <div className="text-sm text-slate-200">{OPERATION_LABEL[r.operation]} <span className="ml-2 text-xs text-slate-500">{new Date(r.timestamp).toLocaleString()}</span></div>
              <dl className="mt-2 space-y-1 text-xs text-slate-400">
                <div>Input: {imageName(evidence, r.input_image_id)} · <Hash value={r.input_sha256} /></div>
                <div>Output: {imageName(evidence, r.output_image_id)} · <Hash value={r.output_sha256} /></div>
                <div>Parameters: <span className="font-mono">{JSON.stringify(r.parameters)}</span></div>
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
        )}
      </Panel>
    </>
  );
}

export default function Provenance() {
  return (
    <section>
      <PageHeader title="Provenance" subtitle="What happened, to which image, when, by which operation, producing what result" />
      <RequireEvidence>{() => <Chain />}</RequireEvidence>
    </section>
  );
}
