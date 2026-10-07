import { Hash, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { formatPsnr } from "../features/format";

const OP_LABEL = { lsb_steganography_embed: "LSB steganography embed", watermark_embed: "Watermark embed" };

function Chain() {
  const { evidence } = useEvidence();
  if (!evidence) return null;
  return (
    <>
      <Panel title="Source evidence">
        <div className="text-sm">{evidence.original_filename} <span className="font-mono text-xs text-slate-500">{evidence.evidence_id}</span></div>
        <div className="mt-1 text-xs text-slate-400">SHA-256 <Hash value={evidence.sha256} /></div>
      </Panel>
      {evidence.provenance.length === 0 && <p className="text-sm text-slate-400">No processing steps recorded yet.</p>}
      {evidence.provenance.map((r) => (
        <Panel key={r.record_id} title={`↓ ${OP_LABEL[r.operation]}`}>
          <dl className="space-y-1 text-xs text-slate-400">
            <div>Time: {new Date(r.timestamp).toLocaleString()}</div>
            <div>Input SHA-256: <Hash value={r.input_sha256} /></div>
            <div>Output SHA-256: <Hash value={r.output_sha256} /></div>
            <div>Parameters: <span className="font-mono">{JSON.stringify(r.parameters)}</span></div>
            <div>MSE {r.metrics.mse.toFixed(6)} · PSNR {formatPsnr(r.metrics.psnr_db)} · SSIM {r.metrics.ssim.toFixed(6)}</div>
          </dl>
          <p className="mt-2 text-xs text-slate-500">Payloads, messages and keys are never recorded.</p>
        </Panel>
      ))}
    </>
  );
}

export default function Provenance() {
  return (
    <section>
      <PageHeader title="Provenance" subtitle="Processing chain for the active evidence: every derived image is linked to its source by SHA-256" />
      <RequireEvidence>{() => <Chain />}</RequireEvidence>
    </section>
  );
}
