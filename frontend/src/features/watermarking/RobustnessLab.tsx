import { useEffect, useState } from "react";
import DifferenceImage from "../../components/DifferenceImage";
import { Button, ErrorText, inputClass, Panel, Toggle } from "../../components/ui";
import { RobustnessTable } from "../../components/watermark";
import { embedWatermark, imageUrl, listAttacks, runAttack, runRobustness } from "../../services/api";
import type { ImageSummary } from "../../types/evidence";
import type { AttackInfo, RobustnessRow, WatermarkMethod } from "../../types/watermark";
import { useEvidence } from "../evidence/EvidenceContext";
import { MAX_MESSAGE_BYTES, METHOD_LABEL } from "../operations";
import { useRunner } from "../useRunner";

interface Marked {
  image: ImageSummary;
  method: WatermarkMethod;
  message: string;
  key: string;
}

export default function RobustnessLab({ evidenceId }: { evidenceId: string }) {
  const { refresh } = useEvidence();
  const [method, setMethod] = useState<WatermarkMethod>("dct");
  const [message, setMessage] = useState("VERIDIA");
  const [key, setKey] = useState("");
  const [strength, setStrength] = useState(25);
  const [marked, setMarked] = useState<Marked | null>(null);

  const [attacks, setAttacks] = useState<AttackInfo[]>([]);
  const [attackName, setAttackName] = useState("jpeg");
  const [parameter, setParameter] = useState(75);
  const [last, setLast] = useState<{ image: ImageSummary; row: RobustnessRow } | null>(null);
  const [history, setHistory] = useState<RobustnessRow[]>([]);
  const [suite, setSuite] = useState<RobustnessRow[] | null>(null);
  const { busy, error, run } = useRunner();

  useEffect(() => {
    listAttacks().then(setAttacks).catch(() => setAttacks([]));
  }, []);
  useEffect(() => {
    setMarked(null);
    setLast(null);
    setHistory([]);
    setSuite(null);
  }, [evidenceId]);

  const attack = attacks.find((a) => a.name === attackName);
  const bytes = new TextEncoder().encode(message).length;

  const embed = () =>
    run(
      () => embedWatermark({ evidence_id: evidenceId, method, message, key, ...(method === "dct" ? { strength } : {}) }),
      (r) => {
        setMarked({ image: r.artifact, method, message, key });
        setLast(null);
        setHistory([]);
        setSuite(null);
        void refresh();
      },
    );

  const apply = () =>
    marked &&
    run(
      () => runAttack({ image_id: marked.image.image_id, method: marked.method, attack: attackName, parameter, message: marked.message, key: marked.key }),
      (r) => {
        setLast({ image: r.artifact, row: r.row });
        setHistory((h) => [...h, r.row]);
        void refresh();
      },
    );

  const runSuite = () =>
    marked && run(() => runRobustness({ image_id: marked.image.image_id, method: marked.method, message: marked.message, key: marked.key }), (r) => setSuite(r.rows));

  return (
    <>
      <Panel title="1 · Embed a watermark">
        <Toggle options={(["dct", "spatial_lsb"] as const).map((m) => ({ id: m, label: METHOD_LABEL[m] }))} value={method} onChange={setMethod} />
        <label className="mt-3 block text-xs text-slate-400">Message (1–{MAX_MESSAGE_BYTES[method]} bytes)</label>
        <input value={message} onChange={(e) => setMessage(e.target.value)} className={inputClass} />
        <label className="mt-3 block text-xs text-slate-400">Key (optional)</label>
        <input value={key} onChange={(e) => setKey(e.target.value)} className={inputClass} />
        {method === "dct" && (
          <>
            <label className="mt-3 block text-xs text-slate-400">Strength: {strength}</label>
            <input type="range" min={5} max={60} value={strength} onChange={(e) => setStrength(Number(e.target.value))} className="w-full max-w-sm" />
          </>
        )}
        <div>
          <Button className="mt-3" disabled={busy || !message || bytes > MAX_MESSAGE_BYTES[method]} onClick={embed}>Embed</Button>
        </div>
        {marked && (
          <p className="mt-2 text-xs text-slate-400">
            Watermarked with {METHOD_LABEL[marked.method]} · <span className="font-mono">{marked.image.sha256.slice(0, 16)}…</span>
          </p>
        )}
        <ErrorText message={error} />
      </Panel>

      {marked && (
        <>
          <Panel title="2 · Apply an attack and attempt extraction">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="block text-xs text-slate-400">Attack</label>
                <select
                  value={attackName}
                  onChange={(e) => {
                    setAttackName(e.target.value);
                    setParameter(attacks.find((a) => a.name === e.target.value)?.presets[0] ?? 0);
                  }}
                  className={inputClass}
                >
                  {attacks.map((a) => <option key={a.name} value={a.name}>{a.label}</option>)}
                </select>
              </div>
              {attack && (
                <div>
                  <label className="block text-xs text-slate-400">{attack.parameter_label} ({attack.minimum}–{attack.maximum})</label>
                  <input type="number" step="any" min={attack.minimum} max={attack.maximum} value={parameter} onChange={(e) => setParameter(Number(e.target.value))} className={`${inputClass} w-32`} />
                </div>
              )}
              <Button disabled={busy} onClick={apply}>Apply attack</Button>
            </div>
            {attack && <p className="mt-2 text-xs text-slate-500">Presets: {attack.presets.join(", ")}</p>}

            {last && (
              <div className="mt-4">
                <div className="flex flex-col gap-4 md:flex-row">
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">Attacked image</div>
                    <img src={imageUrl(last.image.image_id)} alt="Attacked" className="max-h-72 w-full rounded border border-slate-800 bg-slate-950 object-contain" />
                    <a href={imageUrl(last.image.image_id, true)} className="mt-1 inline-block text-xs text-cyan-400 underline">Download</a>
                  </div>
                  <DifferenceImage originalId={marked.image.image_id} processedId={last.image.image_id} />
                </div>
                <div className="mt-3"><RobustnessTable rows={[last.row]} /></div>
              </div>
            )}
          </Panel>

          {history.length > 1 && (
            <Panel title="Experiments this session">
              <RobustnessTable rows={history} />
            </Panel>
          )}

          <Panel title="3 · Full attack suite">
            <p className="mb-3 text-sm text-slate-400">Runs every preset of every attack against this watermarked image (results are not stored as artifacts).</p>
            <Button disabled={busy} onClick={runSuite}>{busy ? "Running…" : "Run suite"}</Button>
            {suite && <div className="mt-4"><RobustnessTable rows={suite} /></div>}
          </Panel>
        </>
      )}
    </>
  );
}
