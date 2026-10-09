import { NavLink, Outlet } from "react-router-dom";
import { NAV_ITEMS } from "../features/navigation";

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-200 md:flex-row">
      <aside className="flex w-full shrink-0 flex-col border-b border-slate-800 bg-slate-900 md:w-60 md:border-b-0 md:border-r">
        <div className="border-b border-slate-800 px-5 py-4 md:py-5">
          <div className="text-lg font-semibold tracking-[0.25em] text-white">VERIDIA</div>
          <div className="mt-1 text-xs text-slate-400">Image Provenance &amp; Forensics Workbench</div>
        </div>
        <nav className="flex gap-1 overflow-x-auto p-3 md:block md:flex-1 md:space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `block shrink-0 whitespace-nowrap rounded px-3 py-2 text-sm ${
                  isActive ? "bg-cyan-500/15 text-cyan-300" : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden border-t border-slate-800 px-5 py-3 text-xs text-slate-500 md:block">Research prototype · v0.5.0</div>
      </aside>
      <main className="min-w-0 flex-1 p-4 md:p-8">
        <Outlet />
      </main>
    </div>
  );
}
