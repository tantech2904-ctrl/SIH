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
    <aside className="w-60 shrink-0 border-r border-soc-border bg-soc-panel flex flex-col">
      <div className="px-4 py-3 border-b border-soc-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-gradient-to-br from-soc-accent to-soc-accentDim flex items-center justify-center text-white font-bold text-xs">
            U
          </div>
          <div>
            <div className="text-sm font-bold tracking-wide">ULPF</div>
            <div className="text-2xs text-soc-textDim">SIH 2026 · PS 26156</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {NAV.map((group) => (
          <div key={group.section} className="mb-3">
            <div className="px-4 mb-1 text-2xs uppercase tracking-widest text-soc-textDim">
              {group.section}
            </div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-1.5 text-sm border-l-2 ${
                    isActive
                      ? "border-soc-accent bg-soc-panelAlt text-soc-text"
                      : "border-transparent text-soc-textMuted hover:text-soc-text hover:bg-soc-panelAlt/60"
                  }`
                }
              >
                <item.icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="px-4 py-2 border-t border-soc-border text-2xs text-soc-textDim">
        v0.1.0 · Team The Beetles
      </div>
    </aside>
  );
}