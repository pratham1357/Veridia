import { useEffect, useMemo, useState } from "react";

import { Link } from "react-router-dom";

import ImageComparison from "../components/ImageComparison";

import {

  Button,

  ErrorText,

  inputClass,

  PageHeader,

  Panel,

  RequireEvidence,

} from "../components/ui";

import { useEvidence } from "../features/evidence/EvidenceContext";

import { evidenceSummary } from "../features/evidence/summary";

import {

  embedStego,

  extractStego,

  getCapacity,

  imageUrl,

  embedKeyedLSB,

  extractKeyedLSB,

  embedLSBMatching,

  extractLSBMatching,

} from "../services/api";

import type {

  CapacityReport,

  OperationResult,

  StegoExtractResult,

} from "../types/evidence";



type AdvancedMethod = "keyed" | "matching";



function AdvancedStegoPanel({

  evidenceId,

  method,

  onCreated,

}: {

  evidenceId: string;

  method: AdvancedMethod;

  onCreated: () => void;

}) {

  const isKeyed = method === "keyed";



  const [payload, setPayload] = useState("");

  const [key, setKey] = useState("");

  const [seed, setSeed] = useState("42");

  const [sourceId, setSourceId] = useState("");

  const [payloadBytes, setPayloadBytes] = useState("");

  const [result, setResult] = useState<OperationResult | null>(null);

  const [extracted, setExtracted] = useState<StegoExtractResult | null>(null);

  const [error, setError] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);



  const byteLength = new TextEncoder().encode(payload).length;

  const parsedSeed = Number(seed);

  const validSeed =

    seed.trim() !== "" &&

    Number.isInteger(parsedSeed) &&

    parsedSeed >= 0 &&

    parsedSeed <= 4294967295;



  const parsedPayloadBytes = Number(payloadBytes);

  const validPayloadBytes =

    payloadBytes.trim() !== "" &&

    Number.isInteger(parsedPayloadBytes) &&

    parsedPayloadBytes >= 1 &&

    parsedPayloadBytes <= 100000;



  async function embed() {

    setBusy(true);

    setError(null);

    setExtracted(null);

    setResult(null);



    try {

      const created = isKeyed

        ? await embedKeyedLSB({

            evidence_id: evidenceId,

            payload,

            key,

            bits_per_channel: 1,

          })

        : await embedLSBMatching({

            evidence_id: evidenceId,

            payload,

            seed: parsedSeed,

          });



      setResult(created);

      setSourceId(created.artifact.image_id);

      setPayloadBytes(String(byteLength));

      onCreated();

    } catch (e) {

      setError(e instanceof Error ? e.message : "Embedding failed.");

    } finally {

      setBusy(false);

    }

  }



  async function extract() {

    const id = sourceId.trim();



    if (!id) {

      setError("Enter a source image ID or embed a message first.");

      return;

    }



    if (isKeyed && !key.trim()) {

      setError("Enter the secret key used during embedding.");

      return;

    }



    if (!isKeyed && (!validSeed || !validPayloadBytes)) {

      setError("Enter a valid seed and payload length in bytes.");

      return;

    }



    setBusy(true);

    setError(null);

    setExtracted(null);



    try {

      const recovered = isKeyed

        ? await extractKeyedLSB({

            source_id: id,

            key,

          })

        : await extractLSBMatching({

            source_id: id,

            seed: parsedSeed,

            payload_bytes: parsedPayloadBytes,

          });



      setExtracted(recovered);

    } catch (e) {

      setError(e instanceof Error ? e.message : "Extraction failed.");

    } finally {

      setBusy(false);

    }

  }



  return (

    <Panel

      title={

        isKeyed

          ? "Keyed LSB (pseudorandom order)"

          : "LSB Matching (+1 / -1)"

      }

    >

      <p className="mb-4 text-sm text-slate-400">

        {isKeyed

          ? "Embeds text using key-derived pseudorandom pixel/channel ordering. This is a demonstration mechanism, not production-grade cryptography."

          : "Embeds text by adjusting sample values by +1 or -1 when needed. Extraction requires the same seed and original payload byte length."}

      </p>



      <label className="mb-1 block text-xs text-slate-400">

        Text payload

      </label>

      <textarea

        value={payload}

        onChange={(e) => setPayload(e.target.value)}

        rows={3}

        className={inputClass}

        placeholder="Enter text to hide..."

      />



      <p className="mt-1 text-xs text-slate-500">

        Payload size: {byteLength} bytes

      </p>



      {isKeyed ? (

        <div className="mt-3">

          <label className="mb-1 block text-xs text-slate-400">

            Secret key

          </label>

          <input

            type="password"

            value={key}

            onChange={(e) => setKey(e.target.value)}

            className={inputClass}

            placeholder="Enter a secret key"

            autoComplete="off"

          />

        </div>

      ) : (

        <div className="mt-3">

          <label className="mb-1 block text-xs text-slate-400">

            Seed (0–4294967295)

          </label>

          <input

            type="number"

            min={0}

            max={4294967295}

            step={1}

            value={seed}

            onChange={(e) => setSeed(e.target.value)}

            className={inputClass}

          />

        </div>

      )}



      <Button

        className="mt-3"

        disabled={

          busy ||

          !payload ||

          (isKeyed ? !key.trim() : !validSeed)

        }

        onClick={embed}

      >

        {busy ? "Working..." : "Embed message"}

      </Button>



      {result && (

        <div className="mt-4 rounded border border-slate-800 bg-slate-950 p-3">

          <p className="text-sm font-medium text-emerald-300">

            Stego artifact created

          </p>



          <p className="mt-2 break-all text-xs text-slate-400">

            Image ID: {result.artifact.image_id}

          </p>



          <p className="mt-1 break-all text-xs text-slate-400">

            Provenance record: {result.record.record_id}

          </p>



          <a

            href={imageUrl(result.artifact.image_id, true)}

            className="mt-2 inline-block text-sm text-cyan-400 underline"

          >

            Download {result.artifact.filename}

          </a>



          {result.capacity && (

            <p className="mt-2 text-xs text-slate-400">

              Capacity: {result.capacity.capacity_bytes} bytes ·

              Utilization:{" "}

              {result.capacity.utilization_percent.toFixed(2)}%

            </p>

          )}

        </div>

      )}



      <div className="mt-5 border-t border-slate-800 pt-4">

        <p className="mb-3 text-sm font-medium">Extract a message</p>



        <label className="mb-1 block text-xs text-slate-400">

          Source image ID

        </label>

        <input

          value={sourceId}

          onChange={(e) => setSourceId(e.target.value)}

          className={inputClass}

          placeholder="Enter or paste an image ID"

        />



        {!isKeyed && (

          <div className="mt-3">

            <label className="mb-1 block text-xs text-slate-400">

              Original payload length (bytes)

            </label>

            <input

              type="number"

              min={1}

              max={100000}

              step={1}

              value={payloadBytes}

              onChange={(e) => setPayloadBytes(e.target.value)}

              className={inputClass}

              placeholder="e.g. 25"

            />

          </div>

        )}



        <Button

          className="mt-3"

          disabled={

            busy ||

            !sourceId.trim() ||

            (isKeyed ? !key.trim() : !validSeed || !validPayloadBytes)

          }

          onClick={extract}

        >

          {busy ? "Working..." : "Extract message"}

        </Button>

      </div>



      {extracted && (

        <div className="mt-3 rounded border border-slate-800 bg-slate-950 p-3">

          {extracted.found ? (

            <>

              <p className="text-xs text-emerald-300">

                Extracted {extracted.payload_bytes} bytes

              </p>

              <p className="mt-2 whitespace-pre-wrap break-words font-mono text-sm">

                {extracted.payload}

              </p>

            </>

          ) : (

            <p className="text-sm text-amber-300">

              No payload recovered: {extracted.detail}

            </p>

          )}

        </div>

      )}



      <ErrorText message={error} />

    </Panel>

  );

}



function Workspace({ evidenceId }: { evidenceId: string }) {

  const { evidence, refresh } = useEvidence();



  const [payload, setPayload] = useState("");

  const [capacity, setCapacity] = useState<CapacityReport | null>(null);

  const [result, setResult] = useState<OperationResult | null>(null);

  const [extracted, setExtracted] = useState<StegoExtractResult | null>(null);

  const [error, setError] = useState<string | null>(null);



  useEffect(() => {

    setResult(null);

    setExtracted(null);

    setCapacity(null);

    setError(null);



    getCapacity(evidenceId)

      .then(setCapacity)

      .catch((e) =>

        setError(e instanceof Error ? e.message : "Could not load capacity.")

      );

  }, [evidenceId]);



  const payloadBytes = useMemo(

    () => new TextEncoder().encode(payload).length,

    [payload]

  );



  const cap = capacity?.capacity_bytes ?? 0;

  const over = payloadBytes > cap;

  const utilization = cap ? (100 * payloadBytes) / cap : 0;



  async function run<T>(fn: () => Promise<T>, then: (v: T) => void) {

    setError(null);



    try {

      then(await fn());

    } catch (e) {

      setError(e instanceof Error ? e.message : "Request failed.");

    }

  }



  const embed = () =>

    run(() => embedStego(evidenceId, payload), (r) => {

      setResult(r);

      setExtracted(null);

      void refresh();

    });



  return (

    <>

      <Panel title="Concept">

        <p className="text-sm text-slate-300">

          <strong>Steganography conceals communication</strong>: the goal is

          to hide the existence of a message. This workspace supports

          sequential LSB embedding, key-derived LSB embedding, and LSB

          matching. Compare this with <em>Watermarking</em>, which associates

          identifying information with media for ownership or authentication.

        </p>

      </Panel>



      <Panel title="Embed payload (LSB)">

        <textarea

          value={payload}

          onChange={(e) => setPayload(e.target.value)}

          rows={3}

          placeholder="Text payload to hide..."

          className={inputClass}

        />



        <div className="mt-2 text-xs text-slate-400">

          Payload {payloadBytes} B · Capacity{" "}

          {capacity ? `${cap} B` : "..."} · Utilization{" "}

          {utilization.toFixed(2)}%

          {over && (

            <span className="ml-2 text-red-400">

              Payload exceeds capacity.

            </span>

          )}

        </div>



        <Button

          className="mt-3"

          disabled={!payload || over || !capacity}

          onClick={embed}

        >

          Embed

        </Button>



        <ErrorText message={error} />

      </Panel>



      {result && evidence && (

        <>

          <Panel title="Generated stego image">

            <a

              href={imageUrl(result.artifact.image_id, true)}

              className="text-sm text-cyan-400 underline"

            >

              Download {result.artifact.filename}

            </a>



            <div className="mt-3 flex flex-wrap gap-3">

              <Button

                onClick={() =>

                  run(

                    () => extractStego(result.artifact.image_id),

                    setExtracted

                  )

                }

              >

                Extract from stego image

              </Button>



              <Button

                className="bg-slate-700 hover:bg-slate-600"

                onClick={() =>

                  run(() => extractStego(evidenceId), setExtracted)

                }

              >

                Extract from original

              </Button>

            </div>



            {extracted && (

              <div className="mt-3 rounded border border-slate-800 bg-slate-950 p-3 text-sm">

                {extracted.found ? (

                  <>

                    <span className="text-xs text-slate-500">

                      Extracted payload ({extracted.payload_bytes} B)

                    </span>

                    <div className="mt-1 whitespace-pre-wrap break-words font-mono">

                      {extracted.payload}

                    </div>

                  </>

                ) : (

                  <span className="text-slate-400">

                    No payload recovered: {extracted.detail}

                  </span>

                )}

              </div>

            )}

          </Panel>



          <ImageComparison

            original={evidenceSummary(evidence)}

            processed={result.artifact}

            metrics={result.record.metrics}

            processedLabel="Stego image"

          />

        </>

      )}



      <AdvancedStegoPanel

        evidenceId={evidenceId}

        method="keyed"

        onCreated={() => void refresh()}

      />



      <AdvancedStegoPanel

        evidenceId={evidenceId}

        method="matching"

        onCreated={() => void refresh()}

      />



      <Panel title="Steganalysis">

        <p className="text-sm text-slate-400">

          LSB planes, channel statistics, histograms, chi-square and RS

          analysis are on the{" "}

          <Link to="/steganalysis" className="text-cyan-400 underline">

            Steganalysis

          </Link>{" "}

          page. Select a generated stego image there as the suspected image

          to examine how embedding changes the measurements.

        </p>

      </Panel>

    </>

  );

}



export default function Steganography() {

  return (

    <section>

      <PageHeader

        title="Steganography"

        subtitle="LSB embedding, keyed embedding, matching, and extraction"

      />



      <RequireEvidence>

        {(id) => <Workspace evidenceId={id} />}

      </RequireEvidence>

    </section>

  );

}
