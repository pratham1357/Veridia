import { NavLink, Outlet } from "react-router-dom";
import { NAV_ITEMS } from "../features/navigation";

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-200">
      <aside className="flex w-60 flex-col border-r border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 px-5 py-5">
          <div className="text-lg font-semibold tracking-[0.25em] text-white">VERIDIA</div>
          <div className="mt-1 text-xs text-slate-400">Image Provenance &amp; Forensics Workbench</div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm ${
                  isActive ? "bg-cyan-500/15 text-cyan-300" : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 px-5 py-3 text-xs text-slate-500">Prototype · v0.1.0</div>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
