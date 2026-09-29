import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Database,
  FileWarning,
  ShieldAlert,
  Zap,
  ArrowRight,
  TrendingUp,
  Clock,
  ExternalLink,
  Shield,
  Search,
  PlayCircle,
  X,
} from "lucide-react";
import { useDashboard, useEvents } from "@/hooks/useApi";
import { api } from "@/services/api";
import { StatCard } from "@/components/StatCard";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { SeverityPie } from "@/charts/SeverityPie";
import { ThroughputLine } from "@/charts/ThroughputLine";
import { BarList } from "@/charts/BarList";
import { SeverityBadge } from "@/components/SeverityBadge";
import { formatTime } from "@/utils/format";

interface DemoToast {
  id: number;
  icon: string;
  msg: string;
  link: string;
}

export default function Dashboard() {
  const { data, isLoading, error } = useDashboard();
  const nav = useNavigate();

  // High-Risk triage logs query
  const { data: highRiskEvents, isLoading: highRiskLoading } = useEvents({
    min_risk: 50,
    size: 6,
    page: 1,
  });

  // Real-time live date and time ticker
  const [currentClock, setCurrentClock] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentClock(
        now.toLocaleString(undefined, {
          weekday: "short",
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: true,
        }),
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Demo Mode state
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoProgress, setDemoProgress] = useState(0);
  const [demoToasts, setDemoToasts] = useState<DemoToast[]>([]);
  const toastIdRef = useRef(0);

  const addToast = (icon: string, msg: string, link: string) => {
    const id = ++toastIdRef.current;
    setDemoToasts((prev) => [...prev, { id, icon, msg, link }]);
    setTimeout(() => {
      setDemoToasts((prev) => prev.filter((t) => t.id !== id));
    }, 7000);
  };

  const dismissToast = (id: number) => {
    setDemoToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const runDemo = async () => {
    if (demoRunning) return;
    setDemoRunning(true);
    setDemoProgress(0);

    const BATCHES = 8;

    for (let i = 0; i < BATCHES; i++) {
      try {
        await api.demoRun();
      } catch {
        // non-fatal — backend may still be starting
      }
      setDemoProgress(Math.round(((i + 1) / BATCHES) * 100));

      if (i === 2) {
        addToast(
          "🔴",
          "Critical: SSH Brute Force detected on 203.0.113.66 (check Alerts)",
          "/detection?tab=alerts",
        );
      }
      if (i === 4) {
        addToast(
          "📡",
          "Telemetry flowing: head to Live Stream to see real-time events",
          "/telemetry?tab=live",
        );
      }

      await new Promise((r) => setTimeout(r, 1500));
    }

    setDemoRunning(false);
    setDemoProgress(0);
    addToast("✅", "Demo complete! Dashboard will refresh automatically.", "/dashboard");
  };

  if (isLoading) return <Loading />;
  if (error) return <div className="page-shell"><ErrorBox error={error} /></div>;
  if (!data) return null;

  const hasEvents = data.totals.events > 0;

  return (
    <div className="page-shell space-y-6">
      {/* Top Header Bar with Live Real-Time Date & Time */}
      <div className="page-header">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.24em] text-soc-accent">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
            <span>SOC Telemetry Engine Active</span>
            <span className="text-soc-borderStrong">·</span>
            <span className="flex items-center gap-1 font-mono text-soc-textDim normal-case text-xs">
              <Clock className="h-3 w-3 text-soc-accent" />
              {currentClock || "Synchronizing..."}
            </span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-soc-text sm:text-3xl mt-1">
            SOC Command Center
          </h1>
          <p className="text-xs text-soc-textDim mt-0.5 font-medium">
            Unified SecOps operations, prioritized incident triage, and real-time event telemetry
          </p>
        </div>

        {/* Quick Links + Demo Button */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Run Demo Button */}
          <button
            onClick={runDemo}
            disabled={demoRunning}
            className={`btn !px-4 !py-2 text-xs font-bold rounded-xl shadow-md flex items-center gap-2 transition-all duration-200 border-soc-accent/60 text-soc-accent hover:bg-soc-accent/10 ${
              demoRunning
                ? "opacity-80 cursor-not-allowed"
                : "hover:border-soc-accent hover:shadow-soc-accent/20"
            }`}
            title="Run live demo: fires 11 realistic attack scenarios over 12 seconds"
          >
            {demoRunning ? (
              <>
                <Zap className="h-3.5 w-3.5 animate-pulse text-soc-accent" />
                <span>Demo Running… {demoProgress}%</span>
              </>
            ) : (
              <>
                <PlayCircle className="h-3.5 w-3.5" />
                <span>▶ Run Demo</span>
              </>
            )}
          </button>

          <button
            onClick={() => nav("/telemetry?tab=live")}
            className="btn btn-primary !px-4 !py-2 text-xs font-bold rounded-xl shadow-md flex items-center gap-2"
          >
            <Activity className="h-3.5 w-3.5" />
            <span>Live Stream</span>
            <ArrowRight className="h-3 w-3" />
          </button>
          <button
            onClick={() => nav("/discovery?tab=ingest")}
            className="btn !px-4 !py-2 text-xs font-semibold rounded-xl"
          >
            Ingest Logs
          </button>
        </div>
      </div>

      {/* Demo Progress Bar */}
      {demoRunning && (
        <div className="w-full h-1 rounded-full bg-soc-panelAlt overflow-hidden -mt-3">
          <div
            className="h-full bg-gradient-to-r from-soc-accent via-sky-400 to-indigo-400 transition-all duration-700 ease-out rounded-full"
            style={{ width: `${demoProgress}%` }}
          />
        </div>
      )}

      {!hasEvents ? (
        <div className="panel p-8 text-center border-dashed rounded-2xl">
          <EmptyState
            message="No Telemetry Ingested Yet"
            hint="Click '▶ Run Demo' above to populate with live synthetic data, or upload a sample log file."
          />
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <button
              onClick={runDemo}
              disabled={demoRunning}
              className="btn btn-primary text-xs rounded-xl flex items-center gap-2"
            >
              <PlayCircle className="h-3.5 w-3.5" />
              {demoRunning ? `Running… ${demoProgress}%` : "▶ Run Demo"}
            </button>
            <button
              onClick={() => nav("/discovery?tab=ingest")}
              className="btn text-xs rounded-xl"
            >
              Upload Sample Logs
            </button>
            <button
              onClick={() => nav("/telemetry?tab=connectors")}
              className="btn text-xs rounded-xl"
            >
              Configure Connectors
            </button>
          </div>
        </div>
      ) : null}

      {/* Primary KPI HUD Grid: Clickable to Respective Workspaces */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div
          onClick={() => nav("/discovery?tab=explorer")}
          className="cursor-pointer transition-transform duration-150 hover:-translate-y-0.5"
          title="Click to open Event Explorer"
        >
          <StatCard
            label="Total Ingested"
            value={data.totals.events.toLocaleString()}
            sub="Click to explore events"
            icon={<Database className="w-4 h-4 text-soc-accent" />}
          />
        </div>

        <div
          onClick={() => nav("/pipeline?tab=schema")}
          className="cursor-pointer transition-transform duration-150 hover:-translate-y-0.5"
          title="Click to view CSE Canonical Schema"
        >
          <StatCard
            label="Canonical CSE"
            value={data.totals.canonical_events.toLocaleString()}
            sub="Normalized events"
            icon={<Activity className="w-4 h-4 text-sky-400" />}
          />
        </div>

        <div
          onClick={() => nav("/discovery?tab=explorer")}
          className="cursor-pointer transition-transform duration-150 hover:-translate-y-0.5"
          title="Filter high-risk events"
        >
          <StatCard
            label="High Risk (≥70)"
            value={data.totals.high_risk_events.toLocaleString()}
            sub="Prioritized triage"
            icon={<ShieldAlert className="w-4 h-4 text-amber-500" />}
            accent="text-sev-high"
          />
        </div>

        <div
          onClick={() => nav("/detection?tab=alerts")}
          className="cursor-pointer transition-transform duration-150 hover:-translate-y-0.5"
          title="Click to view Security Alerts"
        >
          <StatCard
            label="Critical Alerts"
            value={data.totals.critical_alerts.toLocaleString()}
            sub={`${data.totals.open_alerts} open alerts`}
            icon={<AlertTriangle className="w-4 h-4 text-red-500" />}
            accent="text-sev-critical"
          />
        </div>

        <div
          onClick={() => nav("/pipeline?tab=quarantine")}
          className="cursor-pointer transition-transform duration-150 hover:-translate-y-0.5"
          title="Click to view Quarantine & Replay"
        >
          <StatCard
            label="Quarantined"
            value={data.totals.quarantined.toLocaleString()}
            sub="Inspect & Replay"
            icon={<FileWarning className="w-4 h-4 text-amber-400" />}
            accent="text-amber-500"
          />
        </div>
      </div>

      {/* PRIORITIZED TRIAGE: High-Risk Logs Workbench */}
      <div className="panel p-4 sm:p-5 rounded-2xl shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 mb-3 border-b border-soc-border">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-xl bg-red-500/10 text-red-500 flex items-center justify-center font-bold">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-soc-text tracking-wide flex items-center gap-2">
                <span>Priority Triage Queue (High Risk Logs)</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-red-500/15 text-red-500 font-bold border border-red-500/30">
                  ACTION REQUIRED
                </span>
              </h2>
              <p className="text-[11px] text-soc-textDim">
                Telemetry flagged with elevated threat risk scores (≥50). Analysts can inspect payloads immediately.
              </p>
            </div>
          </div>

          <button
            onClick={() => nav("/discovery?tab=explorer")}
            className="inline-flex items-center gap-1.5 text-xs text-soc-accent hover:underline font-bold self-start sm:self-auto"
          >
            <span>View All in Explorer</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
        </div>

        {highRiskLoading ? (
          <div className="py-8 text-center text-xs text-soc-textDim">
            Loading priority events...
          </div>
        ) : !highRiskEvents || highRiskEvents.items.length === 0 ? (
          <div className="py-6 text-center text-xs text-soc-textDim">
            No active high-risk events detected. All systems within standard tolerance.
          </div>
        ) : (
          <div className="overflow-x-auto no-scrollbar">
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Severity</th>
                  <th>Risk Score</th>
                  <th>Event Type</th>
                  <th>Source IP</th>
                  <th>Destination IP</th>
                  <th>Message / Summary</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {highRiskEvents.items.map((ev) => (
                  <tr
                    key={ev.event_id}
                    className="hover:bg-soc-panelAlt/60 cursor-pointer transition-colors text-xs"
                    onClick={() => nav(`/events/${ev.event_id}`)}
                  >
                    <td className="whitespace-nowrap font-mono text-[11px] text-soc-textMuted">
                      {formatTime(ev.timestamp)}
                    </td>
                    <td>
                      <SeverityBadge severity={ev.severity} />
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-2 rounded-full bg-soc-panelAlt overflow-hidden border border-soc-border">
                          <div
                            className={`h-full ${
                              (ev.risk_score || 0) >= 70
                                ? "bg-red-500"
                                : (ev.risk_score || 0) >= 50
                                ? "bg-amber-500"
                                : "bg-sky-500"
                            }`}
                            style={{ width: `${Math.min(100, ev.risk_score || 0)}%` }}
                          />
                        </div>
                        <span className="font-mono font-bold text-[11px] text-soc-text">
                          {ev.risk_score ?? "—"}
                        </span>
                      </div>
                    </td>
                    <td className="font-mono text-[11px] text-soc-text">
                      {ev.event_type || ev.detected_format || "generic"}
                    </td>
                    <td className="font-mono text-[11px] text-soc-accent">
                      {ev.source_ip || "—"}
                    </td>
                    <td className="font-mono text-[11px] text-soc-textMuted">
                      {ev.destination_ip || "—"}
                    </td>
                    <td className="max-w-[280px] truncate text-soc-textDim">
                      {ev.message || ev.event_type || "Security telemetry event"}
                    </td>
                    <td>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          nav(`/events/${ev.event_id}`);
                        }}
                        className="btn text-2xs !py-1 !px-2.5 rounded-lg font-bold hover:border-soc-accent"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Analytics Row: Severity Breakdown + Ingestion Velocity */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="panel p-4 rounded-2xl">
          <div className="panel-header !px-0 !pt-0 pb-3 mb-2">
            <span className="panel-title">
              <TrendingUp className="h-3.5 w-3.5 text-soc-accent" />
              <span>Severity Breakdown</span>
            </span>
            <span className="text-[10px] text-soc-textDim uppercase tracking-wider font-mono">
              Live Distribution
            </span>
          </div>
          <SeverityPie data={data.severity_counts} />
        </div>

        <div className="panel p-4 rounded-2xl lg:col-span-2">
          <div className="panel-header !px-0 !pt-0 pb-3 mb-2">
            <div className="flex items-center gap-2">
              <Activity className="h-3.5 w-3.5 text-soc-accent" />
              <span className="panel-title">Hourly Ingestion Velocity</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-mono">
              <span className="text-soc-accent font-bold">
                {data.throughput.events_per_second.toFixed(2)} EPS
              </span>
              <span className="text-soc-borderStrong">|</span>
              <span className="text-soc-textDim">
                {data.throughput.events_last_minute} in last 60s
              </span>
            </div>
          </div>
          <ThroughputLine data={data.hourly_throughput} />
        </div>
      </div>

      {/* Network & Source Breakdowns (Moved cleanly below) */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        <div className="panel p-4 rounded-2xl">
          <BarList
            title="Top Source IPs"
            data={data.top_source_ips.map((x) => ({ label: x.ip, value: x.count }))}
            color="#06b6d4"
          />
        </div>
        <div className="panel p-4 rounded-2xl">
          <BarList
            title="Top Destination IPs"
            data={data.top_destination_ips.map((x) => ({ label: x.ip, value: x.count }))}
            color="#38bdf8"
          />
        </div>
        <div className="panel p-4 rounded-2xl">
          <BarList
            title="Active Products & Vendors"
            data={Object.entries(data.top_vendors).map(([k, v]) => ({ label: k, value: v }))}
            color="#10b981"
          />
        </div>
        <div className="panel p-4 rounded-2xl">
          <BarList
            title="Detected Formats"
            data={Object.entries(data.format_counts).map(([k, v]) => ({ label: k, value: v }))}
            color="#f59e0b"
          />
        </div>
      </div>

      {/* Demo Toast Notification Stack */}
      {demoToasts.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 items-end pointer-events-none">
          {demoToasts.map((toast) => (
            <div
              key={toast.id}
              className="pointer-events-auto animate-in slide-in-from-right-4 fade-in duration-300 flex items-center gap-3 pl-4 pr-3 py-3 rounded-2xl border border-soc-border bg-soc-panel/95 backdrop-blur-sm shadow-2xl cursor-pointer hover:border-soc-accent/60 transition-all duration-200 max-w-sm group"
              onClick={() => {
                dismissToast(toast.id);
                nav(toast.link);
              }}
            >
              <span className="text-lg shrink-0 leading-none">{toast.icon}</span>
              <span className="text-xs font-medium text-soc-text leading-snug flex-1">
                {toast.msg}
              </span>
              <div className="flex items-center gap-1.5 shrink-0">
                <ArrowRight className="h-3.5 w-3.5 text-soc-textDim group-hover:text-soc-accent transition-colors" />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    dismissToast(toast.id);
                  }}
                  className="ml-1 p-0.5 rounded-lg hover:bg-soc-panelAlt text-soc-textDim hover:text-soc-text transition-colors"
                  title="Dismiss"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}