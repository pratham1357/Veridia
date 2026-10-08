import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useEvidence } from "../features/evidence/EvidenceContext";

export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-semibold text-white">{title}</h1>
      <p className="mt-1 text-slate-400">{subtitle}</p>
    </header>
  );
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-6 rounded border border-slate-800 bg-slate-900 p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h2>
      {children}
    </section>
  );
}

export function Hash({ value }: { value: string }) {
  return <code className="break-all font-mono text-xs text-cyan-300">{value}</code>;
}

export function ErrorText({ message }: { message: string | null }) {
  return message ? <p className="mt-2 text-sm text-red-400">{message}</p> : null;
}

export function Button({ className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    />
  );
}

export const inputClass =
  "w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none";

/** Renders children only when evidence is loaded; otherwise points the user at the Evidence page. */
export function RequireEvidence({ children }: { children: (evidenceId: string) => ReactNode }) {
  const { evidence } = useEvidence();
  if (!evidence) {
    return (
      <div className="rounded border border-dashed border-slate-700 p-8 text-sm text-slate-400">
        No active evidence. <Link to="/evidence" className="text-cyan-400 underline">Upload an image</Link> first.
      </div>
    );
  }
  return <>{children(evidence.evidence_id)}</>;
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="mb-6 flex flex-wrap gap-1 border-b border-slate-800">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`-mb-px border-b-2 px-4 py-2 text-sm ${
            value === t.id ? "border-cyan-400 text-cyan-300" : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Toggle<T extends string>({ options, value, onChange }: { options: { id: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      {options.map((o) => (
        <button
          key={o.id}
          onClick={() => onChange(o.id)}
          className={`rounded px-3 py-1 ${value === o.id ? "bg-cyan-500/20 text-cyan-300" : "bg-slate-800 text-slate-400"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
