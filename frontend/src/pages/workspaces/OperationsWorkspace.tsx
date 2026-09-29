import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  LayoutDashboard,
  Radio,
  Server,
  Upload,
} from "lucide-react";
import Dashboard from "@/pages/Dashboard";
import LiveStream from "@/pages/LiveStream";
import Connectors from "@/pages/Connectors";
import Ingest from "@/pages/Ingest";

type TabId = "overview" | "live" | "connectors" | "ingest";

export default function OperationsWorkspace({
  defaultTab = "overview",
}: {
  defaultTab?: TabId;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get("tab") as TabId | null;
  const [activeTab, setActiveTab] = useState<TabId>(urlTab || defaultTab);

  useEffect(() => {
    if (urlTab && urlTab !== activeTab) {
      setActiveTab(urlTab);
    }
  }, [urlTab]);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const tabs: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }>; badge?: string }[] = [
    { id: "overview", label: "SOC Command Center", icon: LayoutDashboard },
    { id: "live", label: "Live Telemetry", icon: Radio, badge: "STREAM" },
    { id: "connectors", label: "Host Connectors", icon: Server },
    { id: "ingest", label: "Manual Ingestion", icon: Upload },
  ];

  return (
    <div className="flex flex-col min-h-full">
      {/* Workspace Header & Sub-Tabs - Snapped flush at top-0 */}
      <div className="shrink-0 border-b border-soc-border bg-soc-panel/95 backdrop-blur-md px-4 sm:px-6 sticky top-0 z-20 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 pt-2.5 pb-0">
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-soc-accent bg-soc-accent/10 px-2 py-0.5 rounded-full border border-soc-accent/20">
              Workspace 01
            </span>
            <h2 className="text-sm font-bold text-soc-text tracking-wide">
              Operations & Ingestion Hub
            </h2>
          </div>

          {/* Tab Pills */}
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`relative flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-t-lg transition-all border-t border-x ${
                    isActive
                      ? "border-soc-border bg-soc-bg text-soc-accent font-bold shadow-sm"
                      : "border-transparent text-soc-textMuted hover:text-soc-text hover:bg-soc-panelAlt/50"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${isActive ? "text-soc-accent" : "text-soc-textDim"}`} />
                  <span>{tab.label}</span>
                  {tab.badge && (
                    <span className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[9px] font-mono font-bold bg-emerald-500/15 text-emerald-500">
                      {tab.badge}
                    </span>
                  )}
                  {isActive && (
                    <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-soc-accent" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tab View Content */}
      <div className="flex-1 bg-soc-bg">
        {activeTab === "overview" && <Dashboard />}
        {activeTab === "live" && <LiveStream />}
        {activeTab === "connectors" && <Connectors />}
        {activeTab === "ingest" && <Ingest />}
      </div>
    </div>
  );
}
