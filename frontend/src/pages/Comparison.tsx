import { useEffect, useState } from "react";
import { AnalysisResultCard } from "../components/analysis";
import { Button, ErrorText, PageHeader, Panel, RequireEvidence } from "../components/ui";
import { useEvidence } from "../features/evidence/EvidenceContext";
import ComparisonView from "../features/investigation/ComparisonView";
import ImagePicker from "../features/investigation/ImagePicker";
import { imageName } from "../features/operations";
import { useRunner } from "../features/useRunner";
import { runAnalysis } from "../services/api";
import type { AnalysisRecord } from "../types/analysis";

function Workspace({ evidenceId }: { evidenceId: string }) {
  const { evidence, refresh } = useEvidence();
  const derived = evidence?.derived_artifacts ?? [];
  const [reference, setReference] = useState(evidenceId);
  const [subject, setSubject] = useState(derived.length ? derived[derived.length - 1].artifact_id : evidenceId);
  const [record, setRecord] = useState<AnalysisRecord | null>(null);
  const { busy, error, run } = useRunner();

  useEffect(() => {
    setReference(evidenceId);
    setRecord(null);
  }, [evidenceId]);

  if (!evidence) return null;
  const compare = () =>
    run(() => runAnalysis(evidenceId, { type: "comparison", subject_id: subject, reference_id: reference }), (r) => {
      setRecord(r);
      void refresh();
    });

  return (
    <>
      <Panel title="Select images">
        <div className="grid gap-4 md:grid-cols-2">
          <ImagePicker evidence={evidence} value={reference} onChange={setReference} label="Reference (e.g. original evidence)" />
          <ImagePicker evidence={evidence} value={subject} onChange={setSubject} label="Derived / suspected image" />
        </div>
        {derived.length === 0 && (
          <p className="mt-3 text-xs text-slate-500">No derived images yet. Create one on the Steganography or Watermarking page.</p>
        )}
        <Button className="mt-3" disabled={busy} onClick={compare}>{busy ? "Comparing…" : "Compare"}</Button>
        <p className="mt-2 text-xs text-slate-500">The comparison is recorded on the evidence and in the timeline.</p>
        <ErrorText message={error} />
      </Panel>
      {record && (
        <AnalysisResultCard record={record} subjectName={imageName(evidence, record.subject_image_id)}>
          <ComparisonView
            record={record}
            referenceName={imageName(evidence, record.reference_image_id ?? evidenceId)}
            subjectName={imageName(evidence, record.subject_image_id)}
          />
        </AnalysisResultCard>
      )}
    </>
  );
}

export default function Comparison() {
  return (
    <section>
      <PageHeader title="Forensic Comparison" subtitle="Reference vs derived or suspected image: difference map, MSE, PSNR, SSIM, histograms and channel statistics" />
      <RequireEvidence>{(id) => <Workspace evidenceId={id} />}</RequireEvidence>
    </section>
  );
}
