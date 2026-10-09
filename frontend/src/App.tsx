import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { EvidenceProvider } from "./features/evidence/EvidenceContext";
import { PLACEHOLDER_PATHS } from "./features/navigation";
import { OperationsProvider } from "./features/provenance/OperationsContext";
import Comparison from "./pages/Comparison";
import Dashboard from "./pages/Dashboard";
import Evidence from "./pages/Evidence";
import Investigation from "./pages/Investigation";
import PlaceholderPage from "./pages/PlaceholderPage";
import Provenance from "./pages/Provenance";
import Reports from "./pages/Reports";
import Steganalysis from "./pages/Steganalysis";
import Steganography from "./pages/Steganography";
import Watermarking from "./pages/Watermarking";

export default function App() {
  return (
    <EvidenceProvider>
      <OperationsProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="investigation" element={<Investigation />} />
          <Route path="provenance" element={<Provenance />} />
          <Route path="steganography" element={<Steganography />} />
          <Route path="steganalysis" element={<Steganalysis />} />
          <Route path="watermarking" element={<Watermarking />} />
          <Route path="comparison" element={<Comparison />} />
          <Route path="reports" element={<Reports />} />
          {PLACEHOLDER_PATHS.map((p) => (
            <Route key={p} path={p.slice(1)} element={<PlaceholderPage />} />
          ))}
          <Route path="*" element={<PlaceholderPage />} />
        </Route>
      </Routes>
      </OperationsProvider>
    </EvidenceProvider>
  );
}
