import { useState, useEffect } from "react";
import { useSearchParams, useLocation } from "react-router-dom";
import {
  FlaskConical,
  HeartPulse,
  Settings as SettingsIcon,
} from "lucide-react";
import TestLab from "@/pages/TestLab";
import Health from "@/pages/Health";
import Settings from "@/pages/Settings";

type TabId = "testlab" | "health" | "settings";

export default function PlatformWorkspace({
  defaultTab = "testlab",
}: {
  defaultTab?: TabId;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const urlTab = searchParams.get("tab") as TabId | null;

  const getInitialTab = (): TabId => {
    if (urlTab) return urlTab;
    if (location.pathname === "/testlab") return "testlab";
    if (location.pathname === "/health") return "health";
    if (location.pathname === "/settings") return "settings";
    return defaultTab;
  };

  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab());

  useEffect(() => {
    if (urlTab) {
      if (urlTab !== activeTab) setActiveTab(urlTab);
    } else {
      if (location.pathname === "/testlab") setActiveTab("testlab");
      else if (location.pathname === "/health") setActiveTab("health");
      else if (location.pathname === "/settings") setActiveTab("settings");
      else setActiveTab(defaultTab);
    }
  }, [urlTab, location.pathname]);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const tabs: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "testlab", label: "Attack Simulation & Test Lab", icon: FlaskConical },
    { id: "health", label: "Cluster & Worker Health", icon: HeartPulse },
    { id: "settings", label: "System Configuration", icon: SettingsIcon },
  ];

  return (
    <div className="flex flex-col min-h-full">
      {/* Workspace Header & High-Contrast Tab Bar */}
      <div className="shrink-0 border-b border-soc-border bg-soc-panel/95 backdrop-blur-md px-4 sm:px-6 sticky top-0 z-20 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pt-3 pb-2.5">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent flex items-center justify-center font-bold">
              <FlaskConical className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-soc-text tracking-tight">
                Platform Administration & Lab
              </h2>
              <p className="text-[11px] text-soc-textDim font-medium">
                Adversary breach emulation, cluster node diagnostics, and engine configuration
              </p>
            </div>
          </div>

          {/* High-Contrast Interactive Tabs */}
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
        {activeTab === "testlab" && <TestLab />}
        {activeTab === "health" && <Health />}
        {activeTab === "settings" && <Settings />}
      </div>
    </div>
  );
}
