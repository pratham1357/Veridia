import { inputClass } from "../../components/ui";
import type { EvidenceArtifact } from "../../types/evidence";
import { evidenceImages } from "../operations";
import { useOperations } from "../provenance/OperationsContext";

/** Select the original evidence or one of its derived artifacts. */
export default function ImagePicker({
  evidence,
  value,
  onChange,
  label,
}: {
  evidence: EvidenceArtifact;
  value: string;
  onChange: (id: string) => void;
  label: string;
}) {
  const { outputLabel } = useOperations();
  return (
    <div>
      <label className="text-xs text-slate-400">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={inputClass}>
        {evidenceImages(evidence, outputLabel).map((img) => (
          <option key={img.id} value={img.id}>
            {img.label} · {img.sha256.slice(0, 10)}…
          </option>
        ))}
      </select>
    </div>
  );
}
