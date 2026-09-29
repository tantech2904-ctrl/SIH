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
} from "lucide-react";
import { useConnectors, useSetConnectorConfig } from "@/hooks/useApi";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime } from "@/utils/format";
import type { Connector } from "@/types";

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

export default function Connectors() {
  const { data, isLoading, error } = useConnectors();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const copyScriptCmd = () => {
    navigator.clipboard
      .writeText(".\\scripts\\ulpf-connector\\run_connector.bat")
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {});
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

          <button
            onClick={copyScriptCmd}
            className="btn !px-3 !py-1.5 rounded-xl border border-soc-border bg-soc-panel text-xs font-mono text-soc-text flex items-center gap-1.5 shadow-sm hover:border-soc-accent"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <Terminal className="h-3.5 w-3.5 text-soc-accent" />
            )}
            <span className="truncate max-w-[200px] sm:max-w-none">
              {copied ? "Copied Command!" : "run_connector.bat"}
            </span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="panel p-8 rounded-2xl"><Loading /></div>
      ) : error ? (
        <div className="panel p-4 rounded-2xl"><ErrorBox error={error} /></div>
      ) : !data || data.items.length === 0 ? (
        <div className="panel p-8 rounded-2xl text-center space-y-6">
          <EmptyState
            message="No Endpoint Connectors Currently Reporting"
            hint="Host connectors send a heartbeat every 60 seconds. Start the connector on any Windows, Linux, or macOS machine."
          />
          <div className="max-w-lg mx-auto rounded-2xl border border-soc-border bg-soc-panelAlt/80 p-5 text-left space-y-3.5 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-soc-text">
              <Terminal className="h-4 w-4 text-soc-accent" />
              <span>Quick Start: Windows Event Log Connector</span>
            </div>
            <p className="text-xs text-soc-textMuted leading-relaxed">
              Launch the native connector agent from your project directory to begin streaming Security, System, and Application logs:
            </p>
            <div className="flex items-center justify-between p-2.5 rounded-xl bg-soc-bg border border-soc-border font-mono text-xs text-soc-accent select-all">
              <span>.\scripts\ulpf-connector\run_connector.bat</span>
              <button
                onClick={copyScriptCmd}
                className="p-1 rounded hover:bg-soc-panelAlt text-soc-textDim hover:text-soc-text transition"
                title="Copy Command"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] text-soc-textDim">
              <div>• Destination: <strong>UDP Port 5140</strong></div>
              <div>• Backlog: <strong>Last 20 events on boot</strong></div>
              <div>• Heartbeat: <strong>Every 60s</strong></div>
              <div>• Offline Spooling: <strong>Zero log loss</strong></div>
            </div>
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