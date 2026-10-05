import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { NAV_ITEMS } from "./features/navigation";
import Dashboard from "./pages/Dashboard";
import Evidence from "./pages/Evidence";
import PlaceholderPage from "./pages/PlaceholderPage";

const PLACEHOLDERS = NAV_ITEMS.filter((n) => !["/", "/evidence"].includes(n.path));

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="evidence" element={<Evidence />} />
        {PLACEHOLDERS.map((n) => (
          <Route key={n.path} path={n.path.slice(1)} element={<PlaceholderPage />} />
        ))}
        <Route path="*" element={<PlaceholderPage />} />
      </Route>
    </Routes>
  );
}
