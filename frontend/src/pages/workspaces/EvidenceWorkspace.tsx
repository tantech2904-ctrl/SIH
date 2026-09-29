import { useState, useEffect } from "react";
import { useSearchParams, useLocation } from "react-router-dom";
import {
  ScrollText,
  FileCheck,
  FileText,
} from "lucide-react";
import Evidence from "@/pages/Evidence";
import AuditLogs from "@/pages/AuditLogs";
import Reports from "@/pages/Reports";

type TabId = "evidence" | "audit" | "reports";

export default function EvidenceWorkspace({
  defaultTab = "evidence",
}: {
  defaultTab?: TabId;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const urlTab = searchParams.get("tab") as TabId | null;

  const getInitialTab = (): TabId => {
    if (urlTab) return urlTab;
    if (location.pathname === "/evidence") return "evidence";
    if (location.pathname === "/audit") return "audit";
    if (location.pathname === "/reports") return "reports";
    return defaultTab;
  };

  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab());

  useEffect(() => {
    if (urlTab) {
      if (urlTab !== activeTab) setActiveTab(urlTab);
    } else {
      if (location.pathname === "/evidence") setActiveTab("evidence");
      else if (location.pathname === "/audit") setActiveTab("audit");
      else if (location.pathname === "/reports") setActiveTab("reports");
      else setActiveTab(defaultTab);
    }
  }, [urlTab, location.pathname]);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const tabs: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "evidence", label: "Evidence Preservation", icon: FileCheck },
    { id: "audit", label: "Cryptographic Audit Ledger", icon: ScrollText },
    { id: "reports", label: "Compliance & Executive Reports", icon: FileText },
  ];

  return (
    <div className="flex flex-col min-h-full">
      {/* Workspace Header & High-Contrast Tab Bar */}
      <div className="shrink-0 border-b border-soc-border bg-soc-panel/95 backdrop-blur-md px-4 sm:px-6 sticky top-0 z-20 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pt-3 pb-2.5">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent flex items-center justify-center font-bold">
              <ScrollText className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-soc-text tracking-tight">
                Forensic Evidence & Chain of Custody
              </h2>
              <p className="text-[11px] text-soc-textDim font-medium">
                WORM tamper-evident storage, SHA-256 integrity verification, and audit hash chains
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
        {activeTab === "evidence" && <Evidence />}
        {activeTab === "audit" && <AuditLogs />}
        {activeTab === "reports" && <Reports />}
      </div>
    </div>
  );
}
