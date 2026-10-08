import { useEffect, useState } from "react";
import ImageComparison from "../components/ImageComparison";
import { ErrorText, inputClass, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import { OUTPUT_LABEL } from "../features/operations";
import { compareImages } from "../services/api";
import type { CompareResult } from "../types/evidence";

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence } = useEvidence();
  const records = evidence?.provenance ?? [];
  const [selected, setSelected] = useState<string>("");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const chosen = records.find((r) => r.output_image_id === selected) ?? records[records.length - 1];

  useEffect(() => {
    if (!chosen) return setResult(null);
    setError(null);
    compareImages(evidenceId, chosen.output_image_id).then(setResult).catch((e) => setError(e.message));
  }, [evidenceId, chosen?.output_image_id]);

  if (records.length === 0) {
    return <p className="text-sm text-slate-400">No processed images yet. Create one on the Steganography or Watermarking page.</p>;
  }

  return (
    <>
      <Panel title="Processed image">
        <select value={chosen?.output_image_id} onChange={(e) => setSelected(e.target.value)} className={inputClass}>
          {records.map((r) => (
            <option key={r.record_id} value={r.output_image_id}>
              {OUTPUT_LABEL[r.operation]} · {new Date(r.timestamp).toLocaleTimeString()} · {r.output_sha256.slice(0, 10)}…
            </option>
          ))}
        </select>
        <ErrorText message={error} />
      </Panel>
      {result && chosen && <ImageComparison original={result.original} processed={result.processed} metrics={result.metrics} processedLabel={OUTPUT_LABEL[chosen.operation]} />}
    </>
  );
}

export default function Comparison() {
  return (
    <section>
      <PageHeader title="Comparison" subtitle="Original vs processed image, with pixel-level quality metrics" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
