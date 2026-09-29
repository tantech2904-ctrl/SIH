import { useState, useEffect } from "react";
import { useSearchParams, useLocation } from "react-router-dom";
import {
  Bell,
  FolderSearch,
  Activity,
  Map,
  ShieldAlert,
  Network,
} from "lucide-react";
import Alerts from "@/pages/Alerts";
import Incidents from "@/pages/Incidents";
import Rules from "@/pages/Rules";
import ATTACK from "@/pages/ATTACK";
import ThreatIntel from "@/pages/ThreatIntel";
import GeoIP from "@/pages/GeoIP";

type TabId = "alerts" | "incidents" | "rules" | "attck" | "threat-intel" | "geoip";

export default function DetectionWorkspace({
  defaultTab = "alerts",
}: {
  defaultTab?: TabId;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const urlTab = searchParams.get("tab") as TabId | null;

  const getInitialTab = (): TabId => {
    if (urlTab) return urlTab;
    if (location.pathname === "/alerts") return "alerts";
    if (location.pathname === "/incidents") return "incidents";
    if (location.pathname === "/rules") return "rules";
    if (location.pathname === "/attck") return "attck";
    if (location.pathname === "/threat-intel") return "threat-intel";
    if (location.pathname === "/geoip") return "geoip";
    return defaultTab;
  };

  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab());

  useEffect(() => {
    if (urlTab) {
      if (urlTab !== activeTab) setActiveTab(urlTab);
    } else {
      if (location.pathname === "/alerts") setActiveTab("alerts");
      else if (location.pathname === "/incidents") setActiveTab("incidents");
      else if (location.pathname === "/rules") setActiveTab("rules");
      else if (location.pathname === "/attck") setActiveTab("attck");
      else if (location.pathname === "/threat-intel") setActiveTab("threat-intel");
      else if (location.pathname === "/geoip") setActiveTab("geoip");
      else setActiveTab(defaultTab);
    }
  }, [urlTab, location.pathname]);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const tabs: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "alerts", label: "Security Alerts", icon: Bell },
    { id: "incidents", label: "Active Incidents", icon: FolderSearch },
    { id: "rules", label: "Correlation Rules", icon: Activity },
    { id: "attck", label: "MITRE ATT&CK Matrix", icon: Map },
    { id: "threat-intel", label: "Threat Feeds (OTX/VT)", icon: ShieldAlert },
    { id: "geoip", label: "GeoIP & ASN Lookup", icon: Network },
  ];

  return (
    <div className="flex flex-col min-h-full">
      {/* Workspace Header & High-Contrast Tab Bar */}
      <div className="shrink-0 border-b border-soc-border bg-soc-panel/95 backdrop-blur-md px-4 sm:px-6 sticky top-0 z-20 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pt-3 pb-2.5">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent flex items-center justify-center font-bold">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-soc-text tracking-tight">
                Threat Detection & Incident Response
              </h2>
              <p className="text-[11px] text-soc-textDim font-medium">
                Sliding correlation rules, MITRE tactics mapping, and external threat intelligence
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
        {activeTab === "alerts" && <Alerts />}
        {activeTab === "incidents" && <Incidents />}
        {activeTab === "rules" && <Rules />}
        {activeTab === "attck" && <ATTACK />}
        {activeTab === "threat-intel" && <ThreatIntel />}
        {activeTab === "geoip" && <GeoIP />}
      </div>
    </div>
  );
}
