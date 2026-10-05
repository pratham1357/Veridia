import { useLocation } from "react-router-dom";
import { NAV_ITEMS } from "../features/navigation";

export default function PlaceholderPage() {
  const { pathname } = useLocation();
  const item = NAV_ITEMS.find((n) => n.path === pathname);
  return (
    <section>
      <h1 className="text-2xl font-semibold text-white">{item?.label ?? "Not found"}</h1>
      <p className="mt-1 text-slate-400">{item?.description}</p>
      <div className="mt-6 rounded border border-dashed border-slate-700 p-8 text-sm text-slate-500">
        Not implemented yet. Planned module.
      </div>
    </section>
  );
}
