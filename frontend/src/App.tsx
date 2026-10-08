import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { EvidenceProvider } from "./features/evidence/EvidenceContext";
import { PLACEHOLDER_PATHS } from "./features/navigation";
import Comparison from "./pages/Comparison";
import Dashboard from "./pages/Dashboard";
import Evidence from "./pages/Evidence";
import PlaceholderPage from "./pages/PlaceholderPage";
import Provenance from "./pages/Provenance";
import Steganalysis from "./pages/Steganalysis";
import Steganography from "./pages/Steganography";
import Watermarking from "./pages/Watermarking";

export default function App() {
  return (
    <EvidenceProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="provenance" element={<Provenance />} />
          <Route path="steganography" element={<Steganography />} />
          <Route path="steganalysis" element={<Steganalysis />} />
          <Route path="watermarking" element={<Watermarking />} />
          <Route path="comparison" element={<Comparison />} />
          {PLACEHOLDER_PATHS.map((p) => (
            <Route key={p} path={p.slice(1)} element={<PlaceholderPage />} />
          ))}
          <Route path="*" element={<PlaceholderPage />} />
        </Route>
      </Routes>
    </EvidenceProvider>
  );
}
