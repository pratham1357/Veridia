import { useCallback, useEffect, useMemo, useState } from "react";
import { useOperations } from "../features/provenance/OperationsContext";
import { imageUrl, verifyChain } from "../services/api";
import type { DerivedArtifact, EvidenceArtifact, EventType, TimelineEvent } from "../types/evidence";
import type { ChainVerification } from "../types/provenance";
import { Button, ErrorText, inputClass } from "./ui";

export const EVENT_LABEL: Record<EventType, string> = {
  evidence_acquired: "Acquired",
  metadata_extracted: "Metadata",
  hash_computed: "Hashed",
  artifact_created: "Artifact",
  analysis_completed: "Analysis",
  report_exported: "Report",
};

const EVENT_STYLE: Record<EventType, string> = {
  evidence_acquired: "bg-cyan-400",
  metadata_extracted: "bg-cyan-400",
  hash_computed: "bg-cyan-400",
  artifact_created: "bg-violet-400",
  analysis_completed: "bg-amber-400",
  report_exported: "bg-emerald-400",
};

const short = (hash: string | null, n = 10) => (hash ? `${hash.slice(0, n)}…` : "—");

/** Copyable short hash. */
export function HashChip({ value, n = 10, title }: { value: string; n?: number; title?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      title={title ?? `${value} (click to copy)`}
      onClick={() => {
        void navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1200);
        });
      }}
      className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono text-[11px] text-cyan-300 hover:bg-slate-700"
    >
      {copied ? "copied" : short(value, n)}
    </button>
  );
}

/** Chronological, hash-chained list of operations actually performed by the application. */
export function Timeline({
  events,
  limit,
  showHashes = false,
  invalid,
}: {
  events: TimelineEvent[];
  limit?: number;
  showHashes?: boolean;
  invalid?: Set<number>;
}) {
  const shown = limit ? events.slice(-limit) : events;
  return (
    <ol className="relative space-y-3 border-l border-slate-800 pl-5">
      {limit && events.length > limit && <li className="text-xs text-slate-500">… {events.length - limit} earlier event(s)</li>}
      {shown.map((e) => {
        const bad = invalid?.has(e.sequence);
        return (
          <li key={e.event_id} className={`relative text-sm ${bad ? "rounded border border-red-500/40 bg-red-500/5 p-2" : ""}`}>
            <span className={`absolute ${bad ? "-left-[2.1rem] top-3.5" : "-left-[1.6rem] top-1.5"} h-2 w-2 rounded-full ${bad ? "bg-red-400" : EVENT_STYLE[e.event_type]}`} />
            <div className="flex flex-wrap items-baseline gap-x-3">
              <span className="font-mono text-xs text-slate-600">#{e.sequence}</span>
              <span className="font-mono text-xs text-slate-500">{new Date(e.timestamp).toLocaleTimeString()}</span>
              <span className="text-[10px] uppercase tracking-wider text-slate-500">{EVENT_LABEL[e.event_type] ?? e.event_type}</span>
              {bad && <span className="text-xs text-red-300">chain inconsistency</span>}
            </div>
            <div className="text-slate-300">{e.description}</div>
            {showHashes && (
              <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
                <span>prev</span>
                <HashChip value={e.previous_hash} n={8} title={`Previous event hash: ${e.previous_hash}`} />
                <span aria-hidden>→</span>
                <span>hash</span>
                <HashChip value={e.hash} n={8} title={`Event hash: ${e.hash}`} />
                {e.content_hash && (
                  <>
                    <span className="ml-2">covers</span>
                    <HashChip value={e.content_hash} n={8} title={`Hash of the covered record: ${e.content_hash}`} />
                  </>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function Node({ artifact, all }: { artifact: DerivedArtifact; all: DerivedArtifact[] }) {
  const { outputLabel } = useOperations();
  return (
    <li className="mt-2">
      <div className="flex flex-wrap items-baseline gap-x-3 text-sm">
        <span className="text-slate-500">↳ {outputLabel(artifact.operation)}</span>
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

// ---- provenance graph (SVG) ------------------------------------------------------------------------

const NODE_W = 210;
const NODE_H = 58;
const COL_GAP = 64;
const ROW_GAP = 14;

interface GraphNode {
  id: string;
  parent: string | null;
  depth: number;
  y: number;
  title: string;
  filename: string;
  sha256: string;
}

const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

/** Layered tree: depth → column; leaves stacked in DFS order; each parent centred on its children. */
function layout(evidence: EvidenceArtifact, outputLabel: (op: string) => string): GraphNode[] {
  const children = new Map<string, DerivedArtifact[]>();
  for (const a of evidence.derived_artifacts) children.set(a.parent_image_id, [...(children.get(a.parent_image_id) ?? []), a]);
  const nodes: GraphNode[] = [];
  let leaf = 0;
  const visit = (id: string, parent: string | null, depth: number, title: string, filename: string, sha: string): number => {
    const node: GraphNode = { id, parent, depth, y: 0, title, filename, sha256: sha };
    nodes.push(node);
    const kids = children.get(id) ?? [];
    node.y = kids.length
      ? kids.map((k) => visit(k.artifact_id, id, depth + 1, outputLabel(k.operation), k.filename, k.sha256)).reduce((a, b) => a + b, 0) / kids.length
      : leaf++;
    return node.y;
  };
  visit(evidence.evidence_id, null, 0, "Original evidence", evidence.original_filename, evidence.sha256);
  return nodes;
}

/** Original → derived artifacts as an SVG graph. Click a node to select it; red nodes failed file verification. */
export function ProvenanceGraph({
  evidence,
  selected,
  onSelect,
  failed,
}: {
  evidence: EvidenceArtifact;
  selected?: string | null;
  onSelect?: (id: string) => void;
  failed?: Set<string>;
}) {
  const { outputLabel, label } = useOperations();
  const nodes = useMemo(() => layout(evidence, outputLabel), [evidence, outputLabel]);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const opOf = new Map(evidence.derived_artifacts.map((a) => [a.artifact_id, a.operation]));
  const depth = Math.max(...nodes.map((n) => n.depth));
  const rows = Math.max(...nodes.map((n) => n.y)) + 1;
  const width = (depth + 1) * NODE_W + depth * COL_GAP + 2;
  const height = rows * (NODE_H + ROW_GAP) - ROW_GAP + 2;
  const pos = (n: GraphNode) => ({ x: 1 + n.depth * (NODE_W + COL_GAP), y: 1 + n.y * (NODE_H + ROW_GAP) });

  return (
    <div className="overflow-x-auto rounded border border-slate-800 bg-slate-950 p-3">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Provenance graph" className="block">
        {nodes.filter((n) => n.parent).map((n) => {
          const p = pos(byId.get(n.parent!)!);
          const c = pos(n);
          const x1 = p.x + NODE_W, y1 = p.y + NODE_H / 2, x2 = c.x, y2 = c.y + NODE_H / 2;
          const mx = (x1 + x2) / 2;
          return (
            <g key={`e-${n.id}`}>
              <path d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} fill="none" stroke="#475569" strokeWidth={1.25} />
              <title>{label(opOf.get(n.id) ?? "")}</title>
            </g>
          );
        })}
        {nodes.map((n) => {
          const { x, y } = pos(n);
          const isSel = selected === n.id;
          const bad = failed?.has(n.id);
          const stroke = bad ? "#f87171" : isSel ? "#22d3ee" : n.parent ? "#334155" : "#0891b2";
          return (
            <g
              key={n.id}
              transform={`translate(${x},${y})`}
              onClick={() => onSelect?.(n.id)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect?.(n.id)}
              tabIndex={onSelect ? 0 : undefined}
              role={onSelect ? "button" : undefined}
              aria-pressed={onSelect ? isSel : undefined}
              aria-label={`${n.title}: ${n.filename}`}
              className={onSelect ? "cursor-pointer focus:outline-none" : ""}
            >
              <rect width={NODE_W} height={NODE_H} rx={4} fill={isSel ? "#083344" : "#0f172a"} stroke={stroke} strokeWidth={isSel || bad ? 2 : 1} />
              <text x={10} y={17} fontSize={10} fill={n.parent ? "#a78bfa" : "#67e8f9"} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>
                {clip(n.title, 30)}
              </text>
              <text x={10} y={34} fontSize={12} fill="#e2e8f0">{clip(n.filename, 30)}</text>
              <text x={10} y={49} fontSize={10} fill="#64748b" fontFamily="ui-monospace, monospace">
                {n.sha256.slice(0, 20)}…{bad ? "  ✕ file check failed" : ""}
              </text>
              <title>{`${n.filename}\nSHA-256 ${n.sha256}`}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ---- chain verification ----------------------------------------------------------------------------

/** Compact status chip; verifies on mount and whenever ``refreshKey`` changes. */
export function ChainBadge({ evidenceId, refreshKey }: { evidenceId: string; refreshKey?: unknown }) {
  const [v, setV] = useState<ChainVerification | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    verifyChain(evidenceId)
      .then((r) => !cancelled && (setV(r), setFailed(false)))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [evidenceId, refreshKey]);
  if (failed) return <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">chain status unavailable</span>;
  if (!v) return <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-500">verifying chain…</span>;
  return v.valid ? (
    <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">Hash chain intact · {v.event_count} events</span>
  ) : (
    <span className="rounded bg-red-500/15 px-2 py-0.5 text-xs text-red-300">Hash chain: {v.issues.length} inconsistenc{v.issues.length === 1 ? "y" : "ies"}</span>
  );
}

/** Full verification: checks, issues, file hashes, and an optional externally recorded head hash. */
export function ChainVerifier({
  evidenceId,
  refreshKey,
  initialHead = "",
  onResult,
}: {
  evidenceId: string;
  refreshKey?: unknown;
  initialHead?: string;
  onResult?: (v: ChainVerification) => void;
}) {
  const [v, setV] = useState<ChainVerification | null>(null);
  const [head, setHead] = useState(initialHead);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (expected: string) => {
      setBusy(true);
      setError(null);
      try {
        const r = await verifyChain(evidenceId, expected.trim() || null);
        setV(r);
        onResult?.(r);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Verification failed");
      } finally {
        setBusy(false);
      }
    },
    [evidenceId, onResult],
  );

  useEffect(() => {
    void run(head);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evidenceId, refreshKey]);

  const headValid = head.trim() === "" || /^[0-9a-fA-F]{64}$/.test(head.trim());

  return (
    <div className="space-y-4">
      {v && (
        <div className={`flex flex-wrap items-center gap-3 rounded border p-3 ${v.valid ? "border-emerald-500/30 bg-emerald-500/5" : "border-red-500/40 bg-red-500/5"}`}>
          <span className={`text-sm font-semibold ${v.valid ? "text-emerald-300" : "text-red-300"}`}>
            {v.valid ? "All checks passed" : `${v.issues.length} inconsistenc${v.issues.length === 1 ? "y" : "ies"} detected`}
          </span>
          <span className="text-xs text-slate-400">
            {v.event_count} events · verified {new Date(v.verified_at).toLocaleTimeString()}
            {v.first_invalid_sequence !== null && ` · first affected event #${v.first_invalid_sequence}`}
          </span>
          {v.head_hash && (
            <span className="ml-auto flex items-center gap-2 text-xs text-slate-400">
              Current head <HashChip value={v.head_hash} n={16} />
            </span>
          )}
        </div>
      )}

      {v && (
        <ul className="grid gap-2 sm:grid-cols-2">
          {v.checks.map((c) => (
            <li key={c.name} className="flex gap-3 rounded border border-slate-800 bg-slate-950 p-2.5 text-sm">
              <span aria-hidden className={`mt-0.5 font-mono text-xs ${c.passed ? "text-emerald-400" : "text-red-400"}`}>{c.passed ? "✓" : "✕"}</span>
              <div>
                <div className="text-slate-200">{c.label}</div>
                <div className="text-xs text-slate-500">{c.detail}</div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {v && v.issues.length > 0 && (
        <div>
          <div className="mb-2 text-xs uppercase tracking-wider text-red-300">Issues</div>
          <ul className="space-y-1.5 text-sm">
            {v.issues.map((i, k) => (
              <li key={k} className="rounded border border-red-500/30 bg-red-500/5 px-3 py-2">
                <span className="mr-2 font-mono text-xs text-red-300">{i.kind}</span>
                {i.sequence !== null && <span className="mr-2 font-mono text-xs text-slate-500">event #{i.sequence}</span>}
                <span className="text-slate-300">{i.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {v && (
        <details>
          <summary className="cursor-pointer text-xs text-slate-400">Stored files ({v.files.length}) re-hashed</summary>
          <table className="mt-2 w-full text-xs">
            <thead className="text-left text-slate-500">
              <tr><th className="py-1 pr-3">File</th><th className="pr-3">Kind</th><th className="pr-3">Recorded SHA-256</th><th>Status</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {v.files.map((f) => (
                <tr key={f.file_id}>
                  <td className="py-1 pr-3 font-mono text-slate-400">{f.file_id}</td>
                  <td className="pr-3 text-slate-500">{f.kind}</td>
                  <td className="pr-3"><HashChip value={f.expected_sha256} n={12} /></td>
                  <td className={f.status === "match" ? "text-emerald-400" : "text-red-400"}>{f.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      <div>
        <label className="text-xs text-slate-400" htmlFor="expected-head">Expected head hash (optional)</label>
        <div className="mt-1 flex flex-col gap-2 sm:flex-row">
          <input
            id="expected-head"
            value={head}
            onChange={(e) => setHead(e.target.value)}
            placeholder="64-hex head recorded earlier, e.g. from a report or case file"
            className={`${inputClass} font-mono`}
            spellCheck={false}
          />
          <Button disabled={busy || !headValid} onClick={() => run(head)} className="shrink-0">{busy ? "Verifying…" : "Verify chain"}</Button>
        </div>
        {!headValid && <p className="mt-1 text-xs text-amber-300">A head hash is 64 hexadecimal characters.</p>}
        <p className="mt-2 text-xs text-slate-500">
          The chain detects edits, deletions and reordering inside the record. Truncation or a complete rewrite can only be detected against a head
          hash kept somewhere else; every report records the head it covers.
        </p>
        <ErrorText message={error} />
      </div>
    </div>
  );
}
