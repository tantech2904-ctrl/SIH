import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Radio, Search, Upload, FileSearch, Puzzle, GitBranch,
  ShieldAlert, Activity, Map, Crosshair, Bug, Bell, FolderSearch,
  ScrollText, FlaskConical, FileText, HeartPulse, Settings, Layers, Network,
} from "lucide-react";

const NAV = [
  { section: "Operations", items: [
    { to: "/dashboard", label: "SOC Dashboard", icon: LayoutDashboard },
    { to: "/live", label: "Live Stream", icon: Radio },
    { to: "/events", label: "Event Explorer", icon: Search },
    { to: "/ingest", label: "Log Ingestion", icon: Upload },
  ]},
  { section: "Pipeline", items: [
    { to: "/parsers", label: "Parsers", icon: Puzzle },
    { to: "/schema", label: "CSE Schema", icon: Layers },
    { to: "/mappings", label: "Field Mappings", icon: GitBranch },
    { to: "/drift", label: "Schema Drift", icon: Activity },
    { to: "/quarantine", label: "Quarantine", icon: FileSearch },
    { to: "/format", label: "Format Detection", icon: Crosshair },
    { to: "/unknown", label: "Unknown Analyzer", icon: Bug },
  ]},
  { section: "Intelligence", items: [
    { to: "/threat-intel", label: "Threat Intel", icon: ShieldAlert },
    { to: "/geoip", label: "GeoIP", icon: Network },
    { to: "/attck", label: "MITRE ATT&CK", icon: Map },
  ]},
  { section: "Detection", items: [
    { to: "/rules", label: "Detection Rules", icon: Activity },
    { to: "/alerts", label: "Alerts", icon: Bell },
    { to: "/incidents", label: "Incidents", icon: FolderSearch },
  ]},
  { section: "Evidence", items: [
    { to: "/evidence", label: "Chain of Custody", icon: ScrollText },
    { to: "/audit", label: "Audit Log", icon: ScrollText },
    { to: "/reports", label: "Reports", icon: FileText },
  ]},
  { section: "System", items: [
    { to: "/testlab", label: "Test Lab", icon: FlaskConical },
    { to: "/health", label: "System Health", icon: HeartPulse },
    { to: "/settings", label: "Settings", icon: Settings },
  ]},
];

export function Sidebar() {
  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-soc-border/80 bg-soc-panel/85 backdrop-blur-sm">
      <div className="border-b border-soc-border px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-soc-accentSoft via-soc-accent to-soc-accentDim text-sm font-black text-soc-bg shadow-[0_12px_25px_rgba(52,211,153,0.22)]">
            U
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold tracking-[0.22em] text-soc-text">ULPF</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-soc-textDim">SecOps Suite</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV.map((group) => (
          <div key={group.section} className="mb-4">
            <div className="mb-2 px-3 text-[10px] font-medium uppercase tracking-[0.24em] text-soc-textDim">
              {group.section}
            </div>
            <div className="space-y-1">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg border px-3 py-2 text-sm transition-all duration-200 ${
                      isActive
                        ? "border-soc-accent/80 bg-soc-accent/10 text-soc-text shadow-[inset_0_0_0_1px_rgba(52,211,153,0.1)]"
                        : "border-transparent text-soc-textMuted hover:border-soc-border hover:bg-soc-panelAlt/70 hover:text-soc-text"
                    }`
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-soc-border px-4 py-3 text-[10px] uppercase tracking-[0.22em] text-soc-textDim">
        v0.1.0 · Team - BEETLES
      </div>
    </aside>
  );
}