import { useState } from "react";
import { PageHeader, Panel, RequireEvidence, Tabs } from "../components/ui";
import CompareMethods from "../features/watermarking/CompareMethods";
import EmbedVerify from "../features/watermarking/EmbedVerify";
import RobustnessLab from "../features/watermarking/RobustnessLab";

type Tab = "spatial" | "dct" | "compare" | "robustness";

const TABS: { id: Tab; label: string }[] = [
  { id: "spatial", label: "Spatial Domain" },
  { id: "dct", label: "DCT Domain" },
  { id: "compare", label: "Compare Methods" },
  { id: "robustness", label: "Robustness Testing" },
];

export default function Watermarking() {
  const [tab, setTab] = useState<Tab>("spatial");
  return (
    <section>
      <PageHeader title="Watermarking" subtitle="Spatial- and transform-domain watermarks, with measured imperceptibility and robustness" />
      <Panel title="Watermarking vs. steganography">
        <p className="text-sm text-slate-300">
          <strong>Digital watermarking associates information with media</strong> (ownership, authentication, integrity, provenance). The mark need not be
          secret, but it must be recoverable and verifiable, ideally after the image has been processed. <em>Steganography</em>, by contrast, conceals a
          communication.
        </p>
      </Panel>
      <Tabs tabs={TABS} value={tab} onChange={setTab} />
      <RequireEvidence>
        {(id) => (
          <>
            {tab === "spatial" && <EmbedVerify key="spatial" method="spatial_lsb" evidenceId={id} />}
            {tab === "dct" && <EmbedVerify key="dct" method="dct" evidenceId={id} />}
            {tab === "compare" && <CompareMethods evidenceId={id} />}
            {tab === "robustness" && <RobustnessLab evidenceId={id} />}
          </>
        )}
      </RequireEvidence>
    </section>
  );
}
