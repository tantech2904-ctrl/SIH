import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-soc-bg">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(52,211,153,0.18),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(16,163,74,0.14),_transparent_28%)]" />

      <div className="relative flex h-full w-full">
        <div className="hidden md:block">
          <Sidebar />
        </div>

        <div
          className={`fixed inset-0 z-40 transition md:hidden ${isSidebarOpen ? "visible" : "invisible"}`}
          aria-hidden={!isSidebarOpen}
        >
          <button
            type="button"
            aria-label="Close sidebar"
            className={`absolute inset-0 bg-black/60 transition ${isSidebarOpen ? "opacity-100" : "opacity-0"}`}
            onClick={() => setIsSidebarOpen(false)}
          />

          <div
            className={`absolute left-0 top-0 h-full w-[280px] border-r border-soc-border/80 bg-soc-panel shadow-2xl transition-transform duration-200 ${
              isSidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <Sidebar />
          </div>
        </div>

        <div className="flex flex-1 min-w-0 flex-col">
          <Topbar onMenuClick={() => setIsSidebarOpen((open) => !open)} />
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}