import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Panel } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { getHealth, listEvidence, type HealthResponse } from "../services/api";
import type { EvidenceArtifact } from "../types/evidence";

const MODULES: { name: string; path: string; implemented: boolean; note: string }[] = [
  { name: "Evidence intake & hashing", path: "/evidence", implemented: true, note: "Validation, SHA-256, metadata" },
  { name: "Investigation workflow", path: "/investigation", implemented: true, note: "Findings across all modules for one evidence item" },
  { name: "Integrity analysis", path: "/investigation", implemented: true, note: "Hash verification, JPEG tables, blockiness, channel stats" },
  { name: "LSB steganography", path: "/steganography", implemented: true, note: "Embed, extract, capacity" },
  { name: "Steganalysis", path: "/steganalysis", implemented: true, note: "Channel stats, histograms, chi-square, RS" },
  { name: "Digital watermarking", path: "/watermarking", implemented: true, note: "Spatial (LSB) and DCT-domain" },
  { name: "Robustness testing", path: "/watermarking", implemented: true, note: "JPEG, resize, noise, brightness, contrast, crop" },
  { name: "Forensic comparison", path: "/comparison", implemented: true, note: "Difference map, MSE/PSNR/SSIM, histograms" },
  { name: "Error level analysis", path: "/investigation", implemented: true, note: "Experimental: block-level JPEG recompression error" },
  { name: "Provenance & timeline", path: "/provenance", implemented: true, note: "Provenance graph, SHA-256 hash-chained timeline" },
  { name: "Tamper verification", path: "/provenance", implemented: true, note: "Chain, record, lineage and file-hash checks" },
  { name: "Reporting", path: "/reports", implemented: true, note: "HTML + JSON investigation reports" },
  { name: "Persistent storage", path: "/evidence", implemented: true, note: "JSON records + image files under storage/" },
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
        A workbench that applies spatial- and transform-domain watermarking, LSB steganography and statistical steganalysis to digital images, with measured imperceptibility and robustness, evidence hashing, a tamper-evident provenance record of every processing step and exportable investigation reports.
      </p>

      <Panel title="System">
        <div className={`text-sm ${health ? "text-emerald-400" : error ? "text-red-400" : "text-slate-400"}`}>
          {health ? `Backend online · ${health.service} v${health.version}` : error ? "Backend unreachable" : "Checking…"}
        </div>
        {health && (
          <div className="mt-1 text-xs text-slate-400">
            {health.storage === "persistent" ? "Persistent storage" : "Memory-only storage (VERIDIA_PERSIST=false)"} · {health.evidence_count} evidence item(s)
            {health.storage_load_errors > 0 && <span className="text-amber-300"> · {health.storage_load_errors} stored record(s) could not be loaded (see server log)</span>}
          </div>
        )}
      </Panel>

      <Panel title="Evidence">
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
        <p className="mt-3 text-xs text-slate-500">
          {health?.storage === "memory"
            ? "Evidence is held in server memory and is cleared when the backend restarts."
            : "Evidence records and image files are stored under storage/ and reloaded when the backend restarts."}
        </p>
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
