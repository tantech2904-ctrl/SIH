import React, { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Server,
  Terminal,
  RefreshCw,
  Copy,
  Check,
  Radio,
  Sliders,
  LayoutGrid,
  List,
  Layers,
  Download,
  FileCode,
  Archive,
} from "lucide-react";
import { useConnectors, useSetConnectorConfig } from "@/hooks/useApi";
import { Loading, ErrorBox } from "@/components/Loading";
import { formatTime } from "@/utils/format";
import type { Connector } from "@/types";

type PlatformKey = "windows" | "linux" | "macos";

interface PlatformInfo {
  name: string;
  badge: string;
  tagline: string;
  commandLabel: string;
  installCommand: string;
  scriptName: string;
  scriptEndpoint: string;
  bundleName: string;
  bundleEndpoint: string;
  adapters: string[];
  features: string[];
}

function WindowsLogo({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 88 88" fill="currentColor">
      <path d="M0 12.402l35.689-4.86.016 34.423-35.67.202L0 12.402zm35.67 33.529l.028 34.453L.028 75.48.003 46.126l35.667-.195zM43.742 6.645L87.997 0v41.488l-44.255.277V6.645zm44.255 40.598V88L43.742 81.334V47.502l44.255-.259z" />
    </svg>
  );
}

function LinuxLogo({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12.002 0c-2.3 0-4.048 1.488-4.52 3.864-.176.896-.2 1.956-.2 2.928 0 .528.024 1.056.072 1.584C6.542 9.06 5.378 10.452 4.418 12.18c-1.392 2.508-1.584 4.884-.576 7.104.996 2.196 2.952 3.492 5.856 3.888 1.152.156 2.304.168 3.456.012 2.892-.384 4.86-1.68 5.856-3.876 1.008-2.22.816-4.596-.576-7.104-.96-1.728-2.124-3.12-2.936-3.804.048-.528.072-1.056.072-1.584 0-.972-.024-2.032-.2-2.928C16.05 1.488 14.302 0 12.002 0z" />
    </svg>
  );
}

function AppleLogo({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 170 170" fill="currentColor">
      <path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.7-3.07-7.66-7.85-11.88-14.34-6.42-9.84-11.37-21.57-14.85-35.19-3.48-13.62-5.22-26.68-5.22-39.18 0-14.54 3.73-26.83 11.19-36.87 7.46-10.04 17.1-15.19 28.91-15.45 4.8.02 10.3 1.25 16.5 3.7 6.2 2.45 10.08 3.76 11.64 3.93 2.16-.36 6.36-1.74 12.6-4.14 6.24-2.4 11.78-3.46 16.62-3.18 12.98.63 23.36 5.31 31.13 14.04-11.33 6.84-16.89 16.49-16.68 28.95.22 9.8 4.02 17.92 11.4 24.36 7.38 6.44 16.14 10.06 26.27 10.86-2.27 6.86-5.11 13.93-8.52 21.21zM119.22 33.15c0-7.39 2.65-14.35 7.95-20.89 5.3-6.54 11.78-10.63 19.44-12.26.21 1.08.32 2.05.32 2.91 0 7.49-2.78 14.5-8.34 21.03-5.56 6.53-12.29 10.45-20.19 11.77-.42-.85-.68-1.7-.8-2.56z" />
    </svg>
  );
}

function StatusBadge({ status }: { status: "online" | "stale" | "offline" }) {
  const map = {
    online: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30",
    stale: "text-amber-500 bg-amber-500/10 border-amber-500/30",
    offline: "text-red-400 bg-red-500/10 border-red-500/30",
  };
  const dotColor = {
    online: "bg-emerald-500",
    stale: "bg-amber-500",
    offline: "bg-red-400",
  };
  const label = { online: "Online", stale: "Stale", offline: "Offline" };
  return (
    <span className={`badge border ${map[status]} inline-flex items-center gap-1.5 font-bold`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotColor[status]}`} />
      <span>{label[status]}</span>
    </span>
  );
}

function Toggle({
  on,
  pending,
  onChange,
}: {
  on: boolean;
  pending: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => onChange(!on)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full border transition-colors ${
        on
          ? "bg-soc-accent/40 border-soc-accent"
          : "bg-soc-panelAlt border-soc-border"
      } ${pending ? "opacity-50 cursor-wait" : "cursor-pointer"}`}
      aria-pressed={on}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-soc-text transition-transform ${
          on ? "translate-x-4" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function AdapterRow({
  adapter,
  desiredSet,
  runningSet,
  mutationPending,
  onToggle,
}: {
  connector: Connector;
  adapter: string;
  desiredSet: Set<string> | null;
  runningSet: Set<string>;
  mutationPending: boolean;
  onToggle: (adapter: string, next: boolean) => void;
}) {
  const effectiveDesired = desiredSet ?? runningSet;
  const desiredOn = effectiveDesired.has(adapter);
  const runningOn = runningSet.has(adapter);
  const diverging = desiredSet !== null && desiredOn !== runningOn;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between py-2.5 px-3.5 border-b border-soc-border last:border-b-0 hover:bg-soc-panelAlt/40 transition gap-2">
      <div className="flex items-center gap-3 min-w-0">
        <Toggle
          on={desiredOn}
          pending={mutationPending}
          onChange={(next) => onToggle(adapter, next)}
        />
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-soc-text">{adapter}</span>
          {runningOn && (
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          )}
        </div>
      </div>
      <div className="flex items-center gap-2.5 text-2xs pl-12 sm:pl-0">
        {diverging && (
          <span className="text-amber-500 flex items-center gap-1 font-mono font-medium">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Desired: {desiredOn ? "ON" : "OFF"} · Running: {runningOn ? "ON" : "OFF"} (converging…)
          </span>
        )}
        {!diverging && runningOn && (
          <span className="text-emerald-500 font-bold flex items-center gap-1">
            <span className="h-1 w-1 rounded-full bg-emerald-500" />
            Streaming active
          </span>
        )}
        {!diverging && !runningOn && desiredSet === null && (
          <span className="text-soc-textDim">Idle (local config governs)</span>
        )}
        {!diverging && !runningOn && desiredSet !== null && (
          <span className="text-soc-textDim">Disabled by administrator</span>
        )}
      </div>
    </div>
  );
}

function ExpandedAdaptersManager({ connector }: { connector: Connector }) {
  const setConfig = useSetConnectorConfig();

  const allAdapters = Array.from(
    new Set([...(connector.available_adapters || []), ...(connector.adapters || [])]),
  ).sort();

  if (!connector.available_adapters || connector.available_adapters.length === 0) {
    return (
      <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-500 leading-relaxed">
        This connector has not reported its available adapters yet. Start or restart the host connector script to enable dynamic adapter toggles.
      </div>
    );
  }

  const desiredSet =
    connector.desired_adapters === null ? null : new Set(connector.desired_adapters);
  const runningSet = new Set(connector.adapters || []);

  const onToggle = (adapter: string, next: boolean) => {
    const base = desiredSet === null ? new Set(runningSet) : new Set(desiredSet);
    if (next) base.add(adapter);
    else base.delete(adapter);
    setConfig.mutate({
      id: connector.connector_id,
      body: { desired_adapters: Array.from(base).sort() },
    });
  };

  return (
    <div className="rounded-xl border border-soc-border bg-soc-panelAlt/60 overflow-hidden mt-3">
      <div className="px-3.5 py-2.5 text-2xs font-medium text-soc-textDim border-b border-soc-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 bg-soc-panelAlt">
        <span>
          Toggle host adapter channels. The connector converges within {connector.config_poll_interval_s}s.
        </span>
        {desiredSet === null && (
          <span className="text-soc-accent font-semibold">Local agent configuration active</span>
        )}
      </div>
      <div className="divide-y divide-soc-border">
        {allAdapters.map((name) => (
          <AdapterRow
            key={name}
            connector={connector}
            adapter={name}
            desiredSet={desiredSet}
            runningSet={runningSet}
            mutationPending={setConfig.isPending}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  );
}

function DeployConnectorPanel() {
  const [activePlatform, setActivePlatform] = useState<PlatformKey>("windows");
  const [copied, setCopied] = useState<string | null>(null);

  const origin = typeof window !== "undefined" ? window.location.origin : "";

  const PLATFORMS: Record<PlatformKey, PlatformInfo> = {
    windows: {
      name: "Windows",
      badge: "Native Event Log",
      tagline: "Streams Security (auth, process creation, privileges), System, and Application logs directly into ULPF.",
      commandLabel: "PowerShell One-Line Setup (Admin recommended)",
      installCommand: `irm ${origin}/api/v1/connectors/install.ps1 | iex`,
      scriptName: "run_connector.bat",
      scriptEndpoint: `${origin}/api/v1/connectors/download/script?os=windows&server_url=${encodeURIComponent(origin)}`,
      bundleName: "ulpf-connector-windows.zip",
      bundleEndpoint: `${origin}/api/v1/connectors/download/bundle?os=windows&server_url=${encodeURIComponent(origin)}`,
      adapters: ["winevent", "file_tail", "syslog_udp"],
      features: [
        "Zero-configuration setup pre-targeted to this server host",
        "PowerShell auto-bootstraps missing dependencies on launch",
        "Offline log spooling preserves events during network drops",
      ],
    },
    linux: {
      name: "Linux",
      badge: "systemd journald & syslog",
      tagline: "Streams systemd journald units, ssh/sudo auth events, and /var/log telemetry into ULPF.",
      commandLabel: "Bash One-Line Setup (Host or Server)",
      installCommand: `curl -fsSL ${origin}/api/v1/connectors/install.sh | bash`,
      scriptName: "run_connector.sh",
      scriptEndpoint: `${origin}/api/v1/connectors/download/script?os=linux&server_url=${encodeURIComponent(origin)}`,
      bundleName: "ulpf-connector-linux.zip",
      bundleEndpoint: `${origin}/api/v1/connectors/download/bundle?os=linux&server_url=${encodeURIComponent(origin)}`,
      adapters: ["journald", "file_tail", "syslog_udp"],
      features: [
        "Continuous journald stream with automatic unit categorization",
        "Auto-creates python virtual environment and downloads requirements",
        "Pre-configured to stream to this server address automatically",
      ],
    },
    macos: {
      name: "Apple macOS",
      badge: "Apple Unified Log",
      tagline: "Streams macOS log stream (auth, sudo, security subsystem) and local system logs into ULPF.",
      commandLabel: "Terminal One-Line Setup (zsh / bash)",
      installCommand: `curl -fsSL ${origin}/api/v1/connectors/install.sh | bash`,
      scriptName: "run_connector_mac.sh",
      scriptEndpoint: `${origin}/api/v1/connectors/download/script?os=macos&server_url=${encodeURIComponent(origin)}`,
      bundleName: "ulpf-connector-macos.zip",
      bundleEndpoint: `${origin}/api/v1/connectors/download/bundle?os=macos&server_url=${encodeURIComponent(origin)}`,
      adapters: ["macos_log", "file_tail", "syslog_udp"],
      features: [
        "Zero-dependency runner using native macOS unified log stream",
        "Captures interactive terminal actions, privilege escalations, and system events",
        "Pre-wired with current server hostname and auto-syncing adapter channels",
      ],
    },
  };

  const info = PLATFORMS[activePlatform];

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(id);
      setTimeout(() => setCopied(null), 2500);
    });
  };

  const handleDownload = (url: string, filename: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div className="rounded-2xl border border-soc-border bg-soc-panel overflow-hidden shadow-sm">
      {/* Panel Header */}
      <div className="p-4 sm:p-5 border-b border-soc-border flex flex-col md:flex-row md:items-center justify-between gap-3 bg-soc-panelAlt/30">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-soc-accent animate-pulse" />
            <h3 className="text-sm font-bold text-soc-text uppercase tracking-wider">
              Deploy Remote Host Connector
            </h3>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-soc-accent/15 text-soc-accent border border-soc-accent/30">
              Cross-Platform
            </span>
          </div>
          <p className="text-xs text-soc-textDim mt-1">
            Install and run on any target machine to stream telemetry directly to this hosted instance.
          </p>
        </div>

        {/* Platform Tabs */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-soc-panel border border-soc-border self-start md:self-auto">
          <button
            onClick={() => setActivePlatform("windows")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition ${
              activePlatform === "windows"
                ? "bg-soc-accent text-white shadow-sm"
                : "text-soc-textDim hover:text-soc-text hover:bg-soc-panelAlt"
            }`}
          >
            <WindowsLogo className="h-3.5 w-3.5" />
            <span>Windows</span>
          </button>

          <button
            onClick={() => setActivePlatform("linux")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition ${
              activePlatform === "linux"
                ? "bg-soc-accent text-white shadow-sm"
                : "text-soc-textDim hover:text-soc-text hover:bg-soc-panelAlt"
            }`}
          >
            <LinuxLogo className="h-3.5 w-3.5" />
            <span>Linux</span>
          </button>

          <button
            onClick={() => setActivePlatform("macos")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition ${
              activePlatform === "macos"
                ? "bg-soc-accent text-white shadow-sm"
                : "text-soc-textDim hover:text-soc-text hover:bg-soc-panelAlt"
            }`}
          >
            <AppleLogo className="h-3.5 w-3.5" />
            <span>Apple macOS</span>
          </button>
        </div>
      </div>

      {/* Platform Content Body */}
      <div className="p-4 sm:p-6 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-soc-border/60">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-base font-bold text-soc-text flex items-center gap-2">
                {activePlatform === "windows" && <WindowsLogo className="h-4 w-4 text-soc-accent" />}
                {activePlatform === "linux" && <LinuxLogo className="h-4 w-4 text-soc-accent" />}
                {activePlatform === "macos" && <AppleLogo className="h-4 w-4 text-soc-accent" />}
                <span>{info.name} Telemetry Agent</span>
              </h4>
              <span className="badge border border-soc-accent/30 text-soc-accent bg-soc-accent/10 text-2xs font-mono">
                {info.badge}
              </span>
            </div>
            <p className="text-xs text-soc-textMuted mt-1">
              {info.tagline}
            </p>
          </div>

          {/* Action Download Buttons */}
          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => handleDownload(info.scriptEndpoint, info.scriptName)}
              className="btn btn-primary !py-2 !px-3.5 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm"
              title={`Download direct ${info.scriptName} runner script`}
            >
              <FileCode className="h-3.5 w-3.5" />
              <span>Download {info.scriptName}</span>
              <Download className="h-3.5 w-3.5 opacity-80" />
            </button>

            <button
              onClick={() => handleDownload(info.bundleEndpoint, info.bundleName)}
              className="btn !py-2 !px-3.5 rounded-xl text-xs font-semibold border border-soc-border bg-soc-panelAlt hover:border-soc-accent text-soc-text flex items-center gap-2 transition"
              title="Download standalone zip bundle with full dependencies"
            >
              <Archive className="h-3.5 w-3.5 text-soc-accent" />
              <span>Download Full Zip</span>
              <Download className="h-3.5 w-3.5 text-soc-textDim" />
            </button>
          </div>
        </div>

        {/* 1-Line Quick Install Terminal */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-2xs text-soc-textDim">
            <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-soc-text">
              <Terminal className="h-3.5 w-3.5 text-soc-accent" />
              <span>{info.commandLabel}</span>
            </div>
            <span>Auto-configures target server URL and downloads agent bundle</span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl bg-soc-bg border border-soc-border font-mono text-xs text-soc-accent select-all overflow-x-auto gap-3">
            <span className="truncate">{info.installCommand}</span>
            <button
              onClick={() => handleCopy(info.installCommand, "cmd")}
              className="btn !py-1 !px-2.5 rounded-lg border border-soc-border bg-soc-panelAlt text-2xs font-sans text-soc-text flex items-center gap-1.5 shrink-0 hover:border-soc-accent"
              title="Copy Install Command"
            >
              {copied === "cmd" ? (
                <>
                  <Check className="h-3 w-3 text-emerald-500" />
                  <span className="text-emerald-500 font-bold">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 text-soc-textDim" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Feature Highlights & Active Ingestion Channels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <div className="p-3.5 rounded-xl bg-soc-panelAlt/50 border border-soc-border/70 space-y-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
              Active Ingestion Channels
            </span>
            <div className="flex flex-wrap gap-1.5">
              {info.adapters.map((a) => (
                <span
                  key={a}
                  className="px-2 py-0.5 rounded-md font-mono text-2xs font-semibold bg-soc-bg border border-soc-border text-soc-text flex items-center gap-1"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {a}
                </span>
              ))}
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-soc-panelAlt/50 border border-soc-border/70 space-y-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
              Deployment Highlights
            </span>
            <ul className="text-2xs text-soc-textMuted space-y-1">
              {info.features.map((f, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-soc-accent font-bold">•</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Connectors() {
  const { data, isLoading, error } = useConnectors();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showDeploy, setShowDeploy] = useState<boolean>(true);
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="page-shell space-y-6 max-w-full">
      {/* Header */}
      <div className="page-header">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.24em] text-soc-accent">
            <Radio className="h-3 w-3" />
            <span>Endpoint Agents & Log Forwarders</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-soc-text sm:text-3xl mt-1">
            Host Connectors
          </h1>
          <p className="text-xs text-soc-textDim mt-0.5">
            Cross-platform telemetry agents streaming Windows Event Log, Linux journald, and Syslog UDP into ULPF
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Deploy Remote Connector Toggle */}
          <button
            onClick={() => setShowDeploy((prev) => !prev)}
            className={`btn !px-3 !py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 shadow-sm transition ${
              showDeploy
                ? "bg-soc-accent/15 border-soc-accent text-soc-accent"
                : "bg-soc-panel border-soc-border text-soc-text hover:border-soc-accent"
            }`}
          >
            <Download className="h-3.5 w-3.5" />
            <span>{showDeploy ? "Hide Deploy Options" : "Deploy Remote Agent"}</span>
          </button>

          {/* View Mode Toggle */}
          <div className="flex items-center p-1 rounded-xl bg-soc-panelAlt border border-soc-border">
            <button
              onClick={() => setViewMode("cards")}
              className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                viewMode === "cards"
                  ? "bg-soc-accent text-white shadow-sm"
                  : "text-soc-textDim hover:text-soc-text"
              }`}
              title="Card view: fields stacked above values"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Cards</span>
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                viewMode === "table"
                  ? "bg-soc-accent text-white shadow-sm"
                  : "text-soc-textDim hover:text-soc-text"
              }`}
              title="Table view"
            >
              <List className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Table</span>
            </button>
          </div>
        </div>
      </div>

      {/* Deploy Remote Agent Panel */}
      {showDeploy && <DeployConnectorPanel />}

      {/* Main Content Area */}
      {isLoading ? (
        <div className="panel p-8 rounded-2xl"><Loading /></div>
      ) : error ? (
        <div className="panel p-4 rounded-2xl"><ErrorBox error={error} /></div>
      ) : !data || data.items.length === 0 ? (
        <div className="panel p-8 rounded-2xl text-center space-y-4">
          <div className="h-12 w-12 rounded-2xl bg-soc-accent/10 border border-soc-accent/30 text-soc-accent flex items-center justify-center mx-auto">
            <Server className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-soc-text">No Endpoint Connectors Currently Reporting</h3>
            <p className="text-xs text-soc-textDim max-w-md mx-auto">
              Host connectors send a heartbeat every 60 seconds. Use the deployment options above to download and launch the connector on your Windows, Linux, or Apple macOS machine.
            </p>
          </div>
        </div>
      ) : viewMode === "cards" ? (
        /* CARD-BASED RESPONSIVE VIEW: ALL FIELDS STRICTLY ABOVE VALUES */
        <div className="space-y-4">
          {data.items.map((c) => {
            const isOpen = expanded.has(c.connector_id);
            return (
              <div
                key={c.connector_id}
                className="panel p-5 rounded-2xl border border-soc-border shadow-sm hover:border-soc-accent/40 transition-all duration-200"
              >
                {/* Card Title Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3.5 border-b border-soc-border">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-2xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent flex items-center justify-center font-bold shrink-0">
                      <Server className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h2 className="text-base font-bold text-soc-text tracking-tight">
                          {c.hostname}
                        </h2>
                        <StatusBadge status={c.status} />
                        <span className="px-2 py-0.5 rounded-full font-mono text-[10px] bg-soc-panelAlt border border-soc-border text-soc-textMuted">
                          {c.os || "Host Endpoint"}
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-soc-textDim mt-0.5">
                        ID: {c.connector_id}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => toggleExpanded(c.connector_id)}
                    className="btn text-xs font-bold !py-1.5 !px-3 rounded-xl flex items-center gap-1.5 self-start sm:self-auto hover:border-soc-accent"
                  >
                    <Sliders className="h-3.5 w-3.5 text-soc-accent" />
                    <span>{isOpen ? "Hide Channel Controls" : "Manage Adapter Channels"}</span>
                    {isOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>
                </div>

                {/* RESPONSIVE FIELDS GRID: Every field label is placed ABOVE its value */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 py-4">
                  {/* Field 1: Status */}
                  <div className="flex flex-col space-y-1 p-2.5 rounded-xl bg-soc-panelAlt/40 border border-soc-border/60">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                      Agent Status
                    </span>
                    <div>
                      <StatusBadge status={c.status} />
                    </div>
                  </div>

                  {/* Field 2: OS Platform */}
                  <div className="flex flex-col space-y-1 p-2.5 rounded-xl bg-soc-panelAlt/40 border border-soc-border/60">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                      OS Platform
                    </span>
                    <span className="text-xs font-mono font-semibold text-soc-text truncate" title={c.os}>
                      {c.os || "Windows Host"}
                    </span>
                  </div>

                  {/* Field 3: Version */}
                  <div className="flex flex-col space-y-1 p-2.5 rounded-xl bg-soc-panelAlt/40 border border-soc-border/60">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                      Agent Version
                    </span>
                    <span className="text-xs font-mono font-bold text-soc-text">
                      v{c.version}
                    </span>
                  </div>

                  {/* Field 4: Last Heartbeat */}
                  <div className="flex flex-col space-y-1 p-2.5 rounded-xl bg-soc-panelAlt/40 border border-soc-border/60">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                      Last Heartbeat
                    </span>
                    <span className="text-xs font-mono text-soc-textMuted whitespace-nowrap truncate">
                      {formatTime(c.last_heartbeat)}
                    </span>
                  </div>

                  {/* Field 5: Last Telemetry Event */}
                  <div className="flex flex-col space-y-1 p-2.5 rounded-xl bg-soc-panelAlt/40 border border-soc-border/60">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                      Last Ingested Event
                    </span>
                    <span className="text-xs font-mono text-soc-textMuted whitespace-nowrap truncate">
                      {c.last_event_at ? formatTime(c.last_event_at) : "No events yet"}
                    </span>
                  </div>

                  {/* Field 6: Total Events */}
                  <div className="flex flex-col space-y-1 p-2.5 rounded-xl bg-soc-panelAlt/40 border border-soc-border/60">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                      Total Ingested
                    </span>
                    <span className="text-xs font-mono font-black text-soc-accent tabular-nums">
                      {c.events_total.toLocaleString()} events
                    </span>
                  </div>
                </div>

                {/* Active Adapters Row: Label above chips */}
                <div className="flex flex-col space-y-1.5 pt-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-soc-textDim">
                    Active Streaming Adapters ({c.adapters.length})
                  </span>
                  <div className="flex flex-wrap gap-2 items-center">
                    {c.adapters && c.adapters.length > 0 ? (
                      c.adapters.map((a) => (
                        <span
                          key={a}
                          className="px-2.5 py-1 rounded-lg bg-soc-accent/10 border border-soc-accent/30 font-mono text-xs text-soc-accent font-semibold flex items-center gap-1.5 shadow-sm"
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-soc-accent animate-pulse" />
                          {a}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-soc-textDim italic">
                        No active streaming channels reported
                      </span>
                    )}
                  </div>
                </div>

                {/* Collapsible Adapter Channels Manager */}
                {isOpen && (
                  <div className="mt-4 pt-3 border-t border-soc-border">
                    <div className="text-xs font-bold text-soc-text mb-2 flex items-center gap-2">
                      <Layers className="h-4 w-4 text-soc-accent" />
                      <span>Remote Adapter Convergence Controls</span>
                    </div>
                    <ExpandedAdaptersManager connector={c} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* TABLE VIEW (WITH HORIZONTAL SCROLL CONTAINMENT) */
        <div className="panel rounded-2xl shadow-sm overflow-hidden">
          <div className="w-full overflow-x-auto no-scrollbar">
            <table className="table text-xs">
              <thead>
                <tr>
                  <th className="w-8"></th>
                  <th>Status</th>
                  <th>Hostname</th>
                  <th>OS</th>
                  <th>Active Adapters</th>
                  <th>Version</th>
                  <th>Last Heartbeat</th>
                  <th>Last Event</th>
                  <th className="text-right">Total Events</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => {
                  const isOpen = expanded.has(c.connector_id);
                  return (
                    <React.Fragment key={c.connector_id}>
                      <tr
                        className="cursor-pointer hover:bg-soc-panelAlt/50 transition-colors"
                        onClick={() => toggleExpanded(c.connector_id)}
                      >
                        <td className="text-soc-textDim pl-4">
                          {isOpen ? (
                            <ChevronDown className="w-4 h-4 text-soc-accent" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </td>
                        <td><StatusBadge status={c.status} /></td>
                        <td className="font-semibold text-soc-text">{c.hostname}</td>
                        <td className="text-soc-textMuted font-mono text-xs">{c.os}</td>
                        <td className="font-mono text-2xs text-soc-accent">
                          {c.adapters.join(", ") || "—"}
                        </td>
                        <td className="text-soc-textDim font-mono text-xs">{c.version}</td>
                        <td className="text-soc-textMuted whitespace-nowrap">
                          {formatTime(c.last_heartbeat)}
                        </td>
                        <td className="text-soc-textMuted whitespace-nowrap">
                          {c.last_event_at ? formatTime(c.last_event_at) : "—"}
                        </td>
                        <td className="text-right font-mono font-semibold text-soc-text pr-4">
                          {c.events_total.toLocaleString()}
                        </td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={9} className="p-4 bg-soc-panelAlt/30 border-b border-soc-border">
                            <ExpandedAdaptersManager connector={c} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Summary Footer */}
      {data && data.items.length > 0 && (
        <div className="flex items-center justify-between text-2xs text-soc-textDim px-1 pt-1">
          <div>
            Total Monitored Endpoints: <span className="font-mono font-bold text-soc-text">{data.total}</span>
          </div>
          <div>
            Click <strong>Manage Adapter Channels</strong> to toggle remote telemetry channels in real time.
          </div>
        </div>
      )}
    </div>
  );
}