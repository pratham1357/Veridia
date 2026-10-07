import { useState } from "react";
import { ErrorText, Hash, PageHeader, Panel } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { formatBytes } from "../features/format";
import { imageUrl, uploadEvidence } from "../services/api";
import type { FieldStatus, MetadataField } from "../types/evidence";

const STATUS_STYLE: Record<FieldStatus, string> = {
  available: "text-emerald-400",
  not_available: "text-slate-500",
  unknown: "text-amber-400",
};

function MetaRow({ label, field }: { label: string; field: MetadataField }) {
  return (
    <tr>
      <td className="py-1.5 pr-6 text-slate-400">{label}</td>
      <td className="py-1.5 pr-6 font-mono">{field.status === "available" ? String(field.value) : "—"}</td>
      <td className={`py-1.5 text-xs ${STATUS_STYLE[field.status]}`}>{field.status.replace("_", " ")}</td>
    </tr>
  );
}

export default function Evidence() {
  const { evidence, setEvidence } = useEvidence();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      setEvidence(await uploadEvidence(file));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  const meta = evidence?.metadata_results;

  return (
    <section>
      <PageHeader title="Evidence" subtitle="Upload an image to register it as source evidence. The original is stored unmodified." />

      <Panel title="Intake">
        <input
          type="file"
          accept=".png,.jpg,.jpeg,.bmp"
          disabled={busy}
          onChange={(e) => onFile(e.target.files?.[0])}
          className="text-sm text-slate-300 file:mr-4 file:rounded file:border-0 file:bg-slate-800 file:px-4 file:py-2 file:text-slate-200"
        />
        <p className="mt-2 text-xs text-slate-500">PNG, JPEG or BMP, up to 10 MB. Type is verified from file content, not just the extension.</p>
        {busy && <p className="mt-2 text-sm text-slate-400">Uploading…</p>}
        <ErrorText message={error} />
      </Panel>

      {evidence && meta && (
        <>
          <Panel title="Evidence record">
            <div className="flex flex-col gap-6 md:flex-row">
              <img src={imageUrl(evidence.evidence_id)} alt="Evidence preview" className="max-h-64 rounded border border-slate-800 bg-slate-950 object-contain" />
              <dl className="min-w-0 space-y-2 text-sm">
                <div><dt className="text-xs text-slate-500">Evidence ID</dt><dd className="font-mono">{evidence.evidence_id}</dd></div>
                <div><dt className="text-xs text-slate-500">SHA-256</dt><dd><Hash value={evidence.sha256} /></dd></div>
                <div><dt className="text-xs text-slate-500">Filename</dt><dd>{evidence.original_filename}</dd></div>
                <div><dt className="text-xs text-slate-500">Detected type</dt><dd>{evidence.file_type.mime_type}</dd></div>
                <div><dt className="text-xs text-slate-500">Size · Dimensions</dt><dd>{formatBytes(evidence.file_size)} · {evidence.width}×{evidence.height}</dd></div>
                <div><dt className="text-xs text-slate-500">Ingested</dt><dd>{new Date(evidence.created_at).toLocaleString()}</dd></div>
              </dl>
            </div>
          </Panel>

          <Panel title="Image metadata">
            <table className="text-sm">
              <tbody>
                <MetaRow label="Format" field={meta.format} />
                <MetaRow label="Width (px)" field={meta.width} />
                <MetaRow label="Height (px)" field={meta.height} />
                <MetaRow label="Color mode" field={meta.mode} />
                <MetaRow label="Bit depth (per channel)" field={meta.bit_depth} />
                <MetaRow label="ICC profile" field={meta.icc_profile} />
              </tbody>
            </table>
          </Panel>

          <Panel title="EXIF">
            {meta.exif.status === "not_available" && <p className="text-sm text-slate-400">No EXIF metadata is present in this file.</p>}
            {meta.exif.status === "unknown" && <p className="text-sm text-amber-400">EXIF data may be present but could not be read.</p>}
            {meta.exif.status === "available" && (
              <table className="text-sm">
                <tbody className="divide-y divide-slate-800">
                  {meta.exif.entries.map((x, i) => (
                    <tr key={i}>
                      <td className="py-1 pr-4 text-xs text-slate-500">{x.ifd}</td>
                      <td className="py-1 pr-6 text-slate-400">{x.tag}</td>
                      <td className="py-1 font-mono text-xs">{typeof x.value === "string" ? x.value : JSON.stringify(x.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="mt-3 text-xs text-slate-500">Metadata can be absent, stripped, or edited; its absence or presence is not proof of anything.</p>
          </Panel>
        </>
      )}
    </section>
  );
}
