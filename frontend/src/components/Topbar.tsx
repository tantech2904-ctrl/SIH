import { useNavigate } from "react-router-dom";
import {
  LogOut,
  User as UserIcon,
  ShieldCheck,
  Menu,
  Sun,
  Moon,
  Compass,
  Activity,
  Building2,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/context/ThemeContext";

export function Topbar({
  onMenuClick,
  onOpenTour,
}: {
  onMenuClick?: () => void;
  onOpenTour?: () => void;
}) {
  const { user, logout } = useAuth();
  const { effectiveTheme, toggleTheme } = useTheme();
  const nav = useNavigate();

  async function handleLogout() {
    await logout();
    nav("/login");
  }

  return (
    <header className="h-16 shrink-0 border-b border-soc-border bg-soc-panel/85 backdrop-blur-md transition-colors duration-200 sticky top-0 z-30">
      <div className="flex h-full items-center justify-between gap-3 px-4 sm:px-6">
        {/* Left: Mobile Menu + SIEM Brand */}
        <div className="flex min-w-0 items-center gap-3">
          {onMenuClick ? (
            <button
              type="button"
              aria-label="Toggle sidebar"
              onClick={onMenuClick}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-soc-border bg-soc-panelAlt text-soc-text transition hover:border-soc-accent md:hidden"
            >
              <Menu className="h-4 w-4" />
            </button>
          ) : null}

          <div className="flex items-center gap-3">
            <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-soc-accent to-soc-accentDim text-sm font-bold text-white shadow-sm">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div className="hidden sm:block">
              <div className="text-xs font-bold tracking-[0.16em] uppercase text-soc-text">
                ULPF SIEM
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-soc-textDim">
                Unified SecOps Telemetry
              </div>
            </div>
          </div>
        </div>

        {/* Right: Telemetry Status, Tour, Theme Toggle, User Profile */}
        <div className="flex items-center gap-2 sm:gap-3 text-xs">
          {/* Live Status Beacon */}
          <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-full border border-soc-border bg-soc-panelAlt/50 text-[11px] font-mono text-soc-textMuted">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-emerald-500 font-semibold uppercase tracking-wider text-[10px]">
              ONLINE
            </span>
            <span className="text-soc-borderStrong">|</span>
            <Activity className="h-3 w-3 text-soc-accent" />
            <span>Pipeline Active</span>
          </div>

          {/* Site Tour Button */}
          {onOpenTour && (
            <button
              onClick={onOpenTour}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-soc-border bg-soc-panelAlt hover:border-soc-accent text-soc-text hover:text-soc-accent transition font-medium text-xs"
              title="Interactive Platform Tour"
            >
              <Compass className="h-3.5 w-3.5 text-soc-accent" />
              <span className="hidden sm:inline">Site Tour</span>
            </button>
          )}

          {/* Light / Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-soc-border bg-soc-panelAlt text-soc-text hover:border-soc-accent transition"
            title={`Switch to ${effectiveTheme === "dark" ? "Light" : "Dark"} mode`}
            aria-label="Toggle Theme"
          >
            {effectiveTheme === "dark" ? (
              <Sun className="h-4 w-4 text-amber-400 transition-transform duration-300 rotate-0 hover:rotate-45" />
            ) : (
              <Moon className="h-4 w-4 text-sky-500 transition-transform duration-300 rotate-0 hover:-rotate-12" />
            )}
          </button>

          {/* User Profile & Logout */}
          {user ? (
            <>
              {/* Tenant / Workspace Badge */}
              <div className="hidden lg:flex items-center gap-1.5 rounded-full border border-soc-accent/40 bg-soc-accent/10 px-2.5 py-1 text-soc-accent">
                <Building2 className="h-3.5 w-3.5" />
                <span className="max-w-[12rem] truncate text-[11px] font-semibold">
                  {user.tenant_name || "Workspace"}
                </span>
              </div>

              <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-soc-border bg-soc-panelAlt px-2.5 py-1 text-soc-textMuted">
                <UserIcon className="h-3.5 w-3.5 text-soc-accent" />
                <span className="max-w-[10rem] truncate text-[11px] font-medium">
                  {user.email}
                </span>
                <span className="ml-1 rounded-full bg-soc-accent/15 px-1.5 py-0.5 text-[9px] font-bold text-soc-accent uppercase">
                  {user.roles.join(", ")}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="btn !px-2.5 !py-1.5 text-xs text-soc-textDim hover:text-red-400 hover:border-red-500/40"
                title="Log Out"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}