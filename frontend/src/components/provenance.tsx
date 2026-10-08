import { OUTPUT_LABEL } from "../features/operations";
import { imageUrl } from "../services/api";
import type { DerivedArtifact, EvidenceArtifact, TimelineEvent } from "../types/evidence";

const EVENT_STYLE: Record<TimelineEvent["event_type"], string> = {
  evidence_acquired: "bg-cyan-400",
  metadata_extracted: "bg-cyan-400",
  hash_computed: "bg-cyan-400",
  artifact_created: "bg-violet-400",
  analysis_completed: "bg-amber-400",
};

/** Chronological list of operations actually performed by the application. */
export function Timeline({ events, limit }: { events: TimelineEvent[]; limit?: number }) {
  const shown = limit ? events.slice(-limit) : events;
  return (
    <ol className="relative space-y-3 border-l border-slate-800 pl-5">
      {limit && events.length > limit && <li className="text-xs text-slate-500">… {events.length - limit} earlier event(s)</li>}
      {shown.map((e) => (
        <li key={e.event_id} className="relative text-sm">
          <span className={`absolute -left-[1.6rem] top-1.5 h-2 w-2 rounded-full ${EVENT_STYLE[e.event_type]}`} />
          <span className="mr-3 font-mono text-xs text-slate-500">{new Date(e.timestamp).toLocaleTimeString()}</span>
          <span className="text-slate-300">{e.description}</span>
        </li>
      ))}
    </ol>
  );
}

function Node({ artifact, all }: { artifact: DerivedArtifact; all: DerivedArtifact[] }) {
  return (
    <li className="mt-2">
      <div className="flex flex-wrap items-baseline gap-x-3 text-sm">
        <span className="text-slate-500">↳ {OUTPUT_LABEL[artifact.operation]}</span>
        <a href={imageUrl(artifact.artifact_id)} target="_blank" rel="noreferrer" className="text-cyan-300 hover:underline">{artifact.filename}</a>
        <span className="font-mono text-xs text-slate-500">{artifact.sha256.slice(0, 16)}…</span>
        <span className="text-xs text-slate-600">{new Date(artifact.created_at).toLocaleTimeString()}</span>
      </div>
      <ChildList parentId={artifact.artifact_id} all={all} />
    </li>
  );
}

function ChildList({ parentId, all }: { parentId: string; all: DerivedArtifact[] }) {
  const direct = all.filter((a) => a.parent_image_id === parentId);
  if (direct.length === 0) return null;
  return (
    <ul className="ml-5 border-l border-slate-800 pl-3">
      {direct.map((a) => <Node key={a.artifact_id} artifact={a} all={all} />)}
    </ul>
  );
}

/** Original evidence with its derived artifacts nested under their parents. */
export function ArtifactTree({ evidence }: { evidence: EvidenceArtifact }) {
  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-3 text-sm">
        <span className="rounded bg-cyan-500/15 px-2 py-0.5 text-xs text-cyan-300">Original evidence</span>
        <span className="text-slate-200">{evidence.original_filename}</span>
        <span className="font-mono text-xs text-slate-500">{evidence.sha256.slice(0, 16)}…</span>
      </div>
      {evidence.derived_artifacts.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">No derived artifacts yet.</p>
      ) : (
        <ChildList parentId={evidence.evidence_id} all={evidence.derived_artifacts} />
      )}
    </div>
  );
}
