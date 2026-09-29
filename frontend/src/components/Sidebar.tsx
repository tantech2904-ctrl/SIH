import { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  Puzzle,
  ShieldAlert,
  ScrollText,
  Sliders,
  Terminal,
  Radio,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeDot?: boolean;
}

const WORKSPACES: NavItem[] = [
  {
    to: "/dashboard",
    label: "SOC Command Center",
    description: "Command HUD & Prioritized Risk Triage",
    icon: LayoutDashboard,
  },
  {
    to: "/telemetry",
    label: "Live Stream & Agents",
    description: "Live Telemetry, Windows & Syslog Connectors",
    icon: Radio,
    badge: "LIVE",
    badgeDot: true,
  },
  {
    to: "/discovery",
    label: "Discovery & Ingestion",
    description: "Event Explorer, Manual Uploads, Format Detect",
    icon: Search,
  },
  {
    to: "/pipeline",
    label: "Log Pipeline & Schema",
    description: "Plug & Play Parsers, Drift, Quarantine, Replay",
    icon: Puzzle,
  },
  {
    to: "/detection",
    label: "Threat Detection & Intel",
    description: "Incidents, Alerts, Rules, MITRE ATT&CK",
    icon: ShieldAlert,
  },
  {
    to: "/evidence",
    label: "Forensics & Audit",
    description: "Chain of Custody, WORM, Audit Ledger",
    icon: ScrollText,
  },
  {
    to: "/platform",
    label: "Platform Admin & Lab",
    description: "Attack Simulation, Cluster Health, Settings",
    icon: Sliders,
  },
];

interface SidebarProps {
  isMobile?: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({ isMobile = false, onCloseMobile }: SidebarProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (isMobile) return false;
    return localStorage.getItem("ulpf.sidebar_collapsed") === "true";
  });

  useEffect(() => {
    if (!isMobile) {
      localStorage.setItem("ulpf.sidebar_collapsed", String(collapsed));
    }
  }, [collapsed, isMobile]);

  const toggleCollapse = () => {
    if (!isMobile) {
      setCollapsed((prev) => !prev);
    }
  };

  return (
    <aside
      className={`relative flex h-full flex-col border-r border-soc-border bg-soc-panel/95 backdrop-blur-md select-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        collapsed && !isMobile ? "w-[76px]" : "w-[275px]"
      }`}
    >
      {/* Brand Header */}
      <div
        className={`border-b border-soc-border py-3.5 flex items-center transition-all duration-300 ${
          collapsed && !isMobile ? "px-3 justify-center" : "px-4 justify-between"
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={toggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Click to expand sidebar" : "Click to collapse sidebar"}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-soc-accent via-sky-500 to-indigo-600 text-sm font-black text-white shadow-md transition-transform duration-200 hover:scale-105 active:scale-95 cursor-pointer"
          >
            <Terminal className="h-5 w-5" />
          </button>

          {(!collapsed || isMobile) && (
            <div
              onClick={toggleCollapse}
              className="min-w-0 animate-in fade-in duration-200 cursor-pointer select-none"
              title="Click to toggle sidebar"
            >
              <div className="text-xs font-black tracking-[0.2em] text-soc-text uppercase truncate">
                ULPF SecOps
              </div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-soc-textDim truncate font-medium">
                Enterprise SIEM
              </div>
            </div>
          )}
        </div>

        {/* Collapse Button (Shown only when expanded on Desktop to avoid overlap) */}
        {!isMobile && !collapsed && (
          <button
            type="button"
            onClick={toggleCollapse}
            aria-label="Collapse sidebar"
            className="h-8 w-8 shrink-0 rounded-xl border border-soc-border bg-soc-panelAlt/80 text-soc-textDim hover:text-soc-text hover:border-soc-accent/60 flex items-center justify-center transition-all duration-200"
            title="Collapse Sidebar"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Unified Navigation List */}
      <div className="flex-1 overflow-y-auto px-2.5 py-4 space-y-1.5 no-scrollbar">
        {(!collapsed || isMobile) && (
          <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-[0.22em] text-soc-textDim">
            Workspaces
          </div>
        )}

        <div className="space-y-1">
          {WORKSPACES.map((item) => {
            const ItemIcon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `group relative flex rounded-2xl transition-all duration-200 border ${
                    collapsed && !isMobile
                      ? "h-11 w-11 mx-auto items-center justify-center"
                      : "flex-col p-3"
                  } ${
                    isActive
                      ? "bg-soc-accent/12 border-soc-accent/50 text-soc-accent shadow-sm"
                      : "border-transparent hover:bg-soc-panelAlt hover:border-soc-border text-soc-textMuted"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {/* Collapsed Mode Icon View */}
                    {collapsed && !isMobile ? (
                      <div className="relative flex items-center justify-center">
                        <ItemIcon
                          className={`h-5 w-5 transition-transform duration-200 group-hover:scale-110 ${
                            isActive
                              ? "text-soc-accent font-bold"
                              : "text-soc-textDim group-hover:text-soc-text"
                          }`}
                        />
                        {item.badgeDot && (
                          <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-emerald-500 border-2 border-soc-panel shadow-sm animate-pulse" />
                        )}

                        {/* Collapsed Floating Tooltip (iOS / One UI style) */}
                        <div className="pointer-events-none fixed left-[84px] z-50 invisible opacity-0 -translate-x-2 transition-all duration-200 group-hover:visible group-hover:opacity-100 group-hover:translate-x-0">
                          <div className="rounded-xl border border-soc-border bg-soc-panel/95 backdrop-blur-md px-3.5 py-2 shadow-xl">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-soc-text">
                                {item.label}
                              </span>
                              {item.badge && (
                                <span className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[9px] font-mono font-bold bg-emerald-500/15 text-emerald-500">
                                  {item.badge}
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-soc-textMuted max-w-[180px] truncate mt-0.5">
                              {item.description}
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* Expanded Full View */
                      <>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div
                              className={`h-7 w-7 rounded-xl flex items-center justify-center transition-colors ${
                                isActive
                                  ? "bg-soc-accent/20 text-soc-accent"
                                  : "bg-soc-panelAlt text-soc-textDim group-hover:text-soc-text"
                              }`}
                            >
                              <ItemIcon className="h-4 w-4 shrink-0" />
                            </div>
                            <span
                              className={`text-xs font-bold truncate ${
                                isActive ? "text-soc-accent" : "text-soc-text"
                              }`}
                            >
                              {item.label}
                            </span>
                          </div>

                          {item.badge && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-emerald-500/15 text-emerald-500 border border-emerald-500/25">
                              {item.badge}
                            </span>
                          )}
                        </div>

                        <p className="text-[11px] text-soc-textDim mt-1.5 truncate pl-9.5 font-normal leading-tight">
                          {item.description}
                        </p>

                        {/* Active Left Indicator Pill */}
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 h-7 w-1 rounded-r-full bg-soc-accent shadow-sm" />
                        )}
                      </>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>
      </div>

      {/* Footer System Status */}
      <div
        className={`border-t border-soc-border py-3 bg-soc-panelAlt/40 flex items-center transition-all duration-300 text-[10px] text-soc-textDim ${
          collapsed && !isMobile
            ? "px-2 justify-center"
            : "px-4 justify-between"
        }`}
      >
        {collapsed && !isMobile ? (
          <div
            className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500"
            title="Telemetry Engine: Online"
          >
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        ) : (
          <>
            <span className="font-mono tracking-wider font-semibold text-soc-accent font-bold">
              Team BEETLES
            </span>
            <span className="flex items-center gap-1.5 font-medium">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-emerald-500 font-semibold">Engine Active</span>
            </span>
          </>
        )}
      </div>
    </aside>
  );
}