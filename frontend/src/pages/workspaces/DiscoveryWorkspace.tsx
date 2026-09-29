import { useState, useEffect } from "react";
import { useSearchParams, useLocation } from "react-router-dom";
import {
  Search,
  Upload,
  Crosshair,
} from "lucide-react";
import EventExplorer from "@/pages/EventExplorer";
import Ingest from "@/pages/Ingest";
import FormatDetection from "@/pages/FormatDetection";

type TabId = "explorer" | "ingest" | "format";

export default function DiscoveryWorkspace({
  defaultTab = "explorer",
}: {
  defaultTab?: TabId;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const urlTab = searchParams.get("tab") as TabId | null;

  const getInitialTab = (): TabId => {
    if (urlTab) return urlTab;
    if (location.pathname === "/events") return "explorer";
    if (location.pathname === "/ingest") return "ingest";
    if (location.pathname === "/format") return "format";
    return defaultTab;
  };

  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab());

  useEffect(() => {
    if (urlTab) {
      if (urlTab !== activeTab) setActiveTab(urlTab);
    } else {
      if (location.pathname === "/events") setActiveTab("explorer");
      else if (location.pathname === "/ingest") setActiveTab("ingest");
      else if (location.pathname === "/format") setActiveTab("format");
      else setActiveTab(defaultTab);
    }
  }, [urlTab, location.pathname]);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const tabs: {
    id: TabId;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
  }[] = [
    { id: "explorer", label: "Event Explorer & Query", icon: Search },
    { id: "ingest", label: "Manual Ingestion", icon: Upload },
    { id: "format", label: "Format Auto-Detection", icon: Crosshair },
  ];

  return (
    <div className="flex flex-col min-h-full">
      {/* Workspace Header & High-Contrast Tabs */}
      <div className="shrink-0 border-b border-soc-border bg-soc-panel/95 backdrop-blur-md px-4 sm:px-6 sticky top-0 z-20 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pt-3 pb-2.5">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent flex items-center justify-center font-bold">
              <Search className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-soc-text tracking-tight">
                Log Discovery & Ingestion
              </h2>
              <p className="text-[11px] text-soc-textDim font-medium">
                Deep canonical query workbench, manual file uploads, and format signature detection
              </p>
            </div>
          </div>

          {/* High-Contrast Tab Buttons */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-soc-panelAlt border border-soc-border overflow-x-auto no-scrollbar">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-bold rounded-lg transition-all whitespace-nowrap ${
                    isActive
                      ? "bg-soc-accent text-white shadow-md shadow-soc-accent/30"
                      : "text-soc-textMuted hover:text-soc-text hover:bg-soc-panel"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tab View Content */}
      <div className="flex-1 bg-soc-bg">
        {activeTab === "explorer" && <EventExplorer />}
        {activeTab === "ingest" && <Ingest />}
        {activeTab === "format" && <FormatDetection />}
      </div>
    </div>
  );
}
