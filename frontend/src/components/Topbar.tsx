import { useNavigate } from "react-router-dom";
import { LogOut, User as UserIcon, ShieldCheck, Menu } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export function Topbar({ onMenuClick }: { onMenuClick?: () => void }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  async function handleLogout() {
    await logout();
    nav("/login");
  }

  return (
    <header className="h-16 shrink-0 border-b border-soc-border/80 bg-soc-panel/80 backdrop-blur-sm">
      <div className="flex h-full items-center justify-between gap-3 px-3 sm:px-4">
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

          <div className="flex min-w-0 items-center gap-2.5">
            <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-soc-accent to-soc-accentDim text-sm font-bold text-soc-bg">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-[10px] font-semibold uppercase tracking-[0.24em] text-soc-textMuted">
                Universal Log Pre-Processing Framework
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 text-xs">
          {user ? (
            <>
              <span className="hidden items-center gap-1.5 rounded-full border border-soc-border bg-soc-panelAlt px-2 py-1 text-soc-textMuted sm:flex">
                <UserIcon className="h-3.5 w-3.5 text-soc-accent" />
                <span className="max-w-[11rem] truncate">{user.email}</span>
                <span className="ml-1 rounded-full bg-soc-accent/15 px-1.5 py-0.5 text-[10px] text-soc-accent">
                  {user.roles.join(", ")}
                </span>
              </span>
              <button onClick={handleLogout} className="btn !px-2.5 !py-1.5 text-xs">
                <LogOut className="h-3.5 w-3.5" /> Logout
              </button>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}