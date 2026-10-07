import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Panel } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { getHealth, listEvidence, type HealthResponse } from "../services/api";
import type { EvidenceArtifact } from "../types/evidence";

const MODULES: { name: string; path: string; implemented: boolean; note: string }[] = [
  { name: "Evidence intake & hashing", path: "/evidence", implemented: true, note: "Validation, SHA-256, metadata" },
  { name: "LSB steganography", path: "/steganography", implemented: true, note: "Embed, extract, LSB-plane inspection" },
  { name: "Digital watermarking", path: "/watermarking", implemented: true, note: "Keyed spatial-domain watermark" },
  { name: "Comparison & metrics", path: "/comparison", implemented: true, note: "MSE, PSNR, SSIM" },
  { name: "Provenance record", path: "/provenance", implemented: true, note: "Hash chain of processing steps" },
  { name: "Integrity / manipulation analysis", path: "/integrity", implemented: false, note: "Planned" },
  { name: "Reporting", path: "/reports", implemented: false, note: "Planned" },
];

export default function Dashboard() {
  const { evidence, setEvidence } = useEvidence();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);
  const [recent, setRecent] = useState<EvidenceArtifact[]>([]);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setError(true));
    listEvidence().then(setRecent).catch(() => setRecent([]));
  }, [evidence]);

  return (
    <section>
      <PageHeader title="VERIDIA" subtitle="Veridia: Tracing Truth Through Digital Images" />
      <p className="-mt-3 mb-6 max-w-2xl text-sm text-slate-400">
        A workbench that applies digital watermarking and steganography techniques to digital images, with evidence hashing and a provenance record of every processing step.
      </p>

      <Panel title="System">
        <div className={`text-sm ${health ? "text-emerald-400" : error ? "text-red-400" : "text-slate-400"}`}>
          {health ? `Backend online · ${health.service} v${health.version}` : error ? "Backend unreachable" : "Checking…"}
        </div>
      </Panel>

      <Panel title="Evidence this session">
        {recent.length === 0 ? (
          <p className="text-sm text-slate-400">None yet. <Link to="/evidence" className="text-cyan-400 underline">Upload an image</Link>.</p>
        ) : (
          <ul className="divide-y divide-slate-800 text-sm">
            {recent.map((e) => (
              <li key={e.evidence_id} className="flex items-center justify-between py-2">
                <span>{e.original_filename} <span className="ml-2 font-mono text-xs text-slate-500">{e.sha256.slice(0, 12)}…</span></span>
                {evidence?.evidence_id === e.evidence_id ? (
                  <span className="text-xs text-cyan-400">active</span>
                ) : (
                  <button onClick={() => setEvidence(e)} className="text-xs text-cyan-400 underline">make active</button>
                )}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-xs text-slate-500">Evidence is held in server memory and is cleared when the backend restarts.</p>
      </Panel>

      <Panel title="Analysis modules">
        <ul className="divide-y divide-slate-800 text-sm">
          {MODULES.map((m) => (
            <li key={m.name} className="flex items-center justify-between py-2">
              {m.implemented ? <Link to={m.path} className="text-slate-200 hover:text-cyan-300">{m.name}</Link> : <span className="text-slate-500">{m.name}</span>}
              <span className={`text-xs ${m.implemented ? "text-emerald-400" : "text-slate-500"}`}>{m.note}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </section>
  );
}
