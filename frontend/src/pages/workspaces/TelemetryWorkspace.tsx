import { useState, useEffect } from "react";
import { useSearchParams, useLocation } from "react-router-dom";
import {
  Radio,
  Server,
  Terminal,
  Copy,
  Check,
  Download,
  FolderOpen,
} from "lucide-react";
import LiveStream from "@/pages/LiveStream";
import Connectors from "@/pages/Connectors";

type TabId = "live" | "connectors";

export default function TelemetryWorkspace({
  defaultTab = "live",
}: {
  defaultTab?: TabId;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const urlTab = searchParams.get("tab") as TabId | null;

  const getInitialTab = (): TabId => {
    if (urlTab) return urlTab;
    if (location.pathname === "/connectors") return "connectors";
    if (location.pathname === "/live") return "live";
    return defaultTab;
  };

  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab());
  const [showConnectorModal, setShowConnectorModal] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);

  useEffect(() => {
    if (urlTab) {
      if (urlTab !== activeTab) setActiveTab(urlTab);
    } else {
      if (location.pathname === "/connectors") setActiveTab("connectors");
      else if (location.pathname === "/live") setActiveTab("live");
      else setActiveTab(defaultTab);
    }
  }, [urlTab, location.pathname]);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const copyCommand = () => {
    navigator.clipboard.writeText("scripts\\ulpf-connector\\run_connector.bat");
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  const tabs: {
    id: TabId;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string;
  }[] = [
    { id: "live", label: "Live Telemetry Stream", icon: Radio, badge: "REALTIME" },
    { id: "connectors", label: "Host Log Connectors & UDP", icon: Server },
  ];

  return (
    <div className="flex flex-col min-h-full">
      {/* Workspace Header & High-Contrast Tabs */}
      <div className="shrink-0 border-b border-soc-border bg-soc-panel/95 backdrop-blur-md px-4 sm:px-6 sticky top-0 z-20 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pt-3 pb-2.5">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent flex items-center justify-center font-bold">
              <Radio className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-soc-text tracking-tight">
                Live Telemetry & Connectors Hub
              </h2>
              <p className="text-[11px] text-soc-textDim font-medium">
                Native Windows Event Log, Linux journald, and Syslog UDP (Port 5140)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Quick Action to Run/Inspect Connector */}
            <button
              onClick={() => setShowConnectorModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-soc-accent/40 bg-soc-accent/10 hover:bg-soc-accent/20 text-xs text-soc-accent font-bold transition shadow-sm"
              title="Launch or configure host connector"
            >
              <Terminal className="h-3.5 w-3.5" />
              <span>Launch Connector (.bat)</span>
            </button>

            {/* High-Contrast Tab Buttons */}
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-soc-panelAlt border border-soc-border">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-bold rounded-lg transition-all ${
                      isActive
                        ? "bg-soc-accent text-white shadow-md shadow-soc-accent/30"
                        : "text-soc-textMuted hover:text-soc-text hover:bg-soc-panel"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{tab.label}</span>
                    {tab.badge && (
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.2 rounded-full font-bold ${
                          isActive
                            ? "bg-white/25 text-white"
                            : "bg-emerald-500/15 text-emerald-500"
                        }`}
                      >
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Tab View Content */}
      <div className="flex-1 bg-soc-bg">
        {activeTab === "live" && <LiveStream />}
        {activeTab === "connectors" && <Connectors />}
      </div>

      {/* Connector Runner & File Path Modal */}
      {showConnectorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-lg rounded-2xl border border-soc-border bg-soc-panel p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-soc-border">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-xl bg-soc-accent/15 text-soc-accent flex items-center justify-center">
                  <Terminal className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-soc-text">
                    Windows & Host Connector Execution
                  </h3>
                  <div className="text-[11px] text-soc-textDim">
                    Tail local Windows Security, System & Application logs into ULPF
                  </div>
                </div>
              </div>
              <button
                onClick={() => setShowConnectorModal(false)}
                className="text-soc-textDim hover:text-soc-text text-sm font-bold p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="rounded-xl border border-soc-border bg-soc-panelAlt p-3.5 space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                  Local Script Location
                </span>
                <div className="flex items-center justify-between gap-2 p-2 rounded-lg bg-soc-bg border border-soc-border font-mono text-[11px] text-soc-text select-all">
                  <span className="truncate">scripts\ulpf-connector\run_connector.bat</span>
                  <button
                    onClick={copyCommand}
                    className="shrink-0 p-1.5 rounded-md hover:bg-soc-panelAlt text-soc-accent transition"
                    title="Copy Command"
                  >
                    {copiedCmd ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-soc-border bg-soc-panelAlt p-3.5 space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                  How To Run Manually
                </span>
                <p className="text-soc-textMuted leading-relaxed">
                  Open a PowerShell or Command Prompt terminal in the project directory (or right-click and Run as Administrator) and run:
                </p>
                <div className="p-2.5 rounded-lg bg-soc-bg border border-soc-border font-mono text-[11px] text-emerald-400">
                  .\scripts\ulpf-connector\run_connector.bat
                </div>
              </div>

              <div className="p-3 rounded-xl border border-soc-accent/20 bg-soc-accent/5 text-[11px] text-soc-text leading-relaxed">
                <strong>Automatic Ingestion:</strong> The connector reads the last 20 backlog events from your Windows Event Log immediately upon boot and streams new events in real time.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-soc-border">
              <button
                onClick={() => setShowConnectorModal(false)}
                className="btn text-xs font-semibold px-4"
              >
                Close
              </button>
              <button
                onClick={copyCommand}
                className="btn btn-primary text-xs font-bold px-4"
              >
                {copiedCmd ? "Copied!" : "Copy Execution Command"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
