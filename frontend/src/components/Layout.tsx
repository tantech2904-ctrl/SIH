import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { SiteTour } from "./SiteTour";

export function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isTourOpen, setIsTourOpen] = useState(false);

  // Check if first-time user hasn't seen the tour yet
  useEffect(() => {
    const hasCompletedTour = localStorage.getItem("ulpf.tour_completed");
    if (!hasCompletedTour) {
      // Small delay on first visit so the UI loads smoothly before opening
      const timer = setTimeout(() => {
        setIsTourOpen(true);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, []);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-soc-bg text-soc-text font-sans antialiased">
      <div className="relative flex h-full w-full">
        {/* Desktop Sidebar */}
        <div className="hidden md:block">
          <Sidebar />
        </div>

        {/* Mobile Drawer */}
        <div
          className={`fixed inset-0 z-40 transition-all duration-200 md:hidden ${
            isSidebarOpen ? "visible opacity-100" : "invisible opacity-0"
          }`}
          aria-hidden={!isSidebarOpen}
        >
          <button
            type="button"
            aria-label="Close sidebar"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setIsSidebarOpen(false)}
          />

          <div
            className={`absolute left-0 top-0 h-full w-[275px] border-r border-soc-border bg-soc-panel shadow-2xl transition-transform duration-200 ${
              isSidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <Sidebar isMobile onCloseMobile={() => setIsSidebarOpen(false)} />
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex flex-1 min-w-0 flex-col overflow-hidden">
          <Topbar
            onMenuClick={() => setIsSidebarOpen((open) => !open)}
            onOpenTour={() => setIsTourOpen(true)}
          />

          <main className="flex-1 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>

      {/* Global Interactive Site Tour Modal */}
      <SiteTour isOpen={isTourOpen} onClose={() => setIsTourOpen(false)} />
    </div>
  );
}