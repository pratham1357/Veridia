import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "../services/api";

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setError(true));
  }, []);

  return (
    <section>
      <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
      <p className="mt-1 text-slate-400">Veridia: Tracing Truth Through Digital Images</p>
      <div className="mt-6 grid max-w-3xl gap-4 sm:grid-cols-2">
        <div className="rounded border border-slate-800 bg-slate-900 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-500">Backend API</div>
          <div className={`mt-2 text-sm ${health ? "text-emerald-400" : error ? "text-red-400" : "text-slate-400"}`}>
            {health ? `Online · ${health.service} v${health.version}` : error ? "Unreachable" : "Checking…"}
          </div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-900 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-500">Active evidence</div>
          <div className="mt-2 text-sm text-slate-400">None. Evidence intake is not implemented yet.</div>
        </div>
      </div>
    </section>
  );
}
