import { useNavigate } from "react-router-dom";
import { LogOut, User as UserIcon, ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export function Topbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  async function handleLogout() {
    await logout();
    nav("/login");
  }

  return (
    <header className="h-11 shrink-0 border-b border-soc-border bg-soc-panel flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <ShieldCheck className="w-4 h-4 text-soc-accent" />
        <span className="text-xs font-semibold tracking-widest uppercase text-soc-textMuted">
          Universal Log Pre-Processing Framework
        </span>
      </div>
      <div className="flex items-center gap-3 text-xs">
        {user ? (
          <>
            <span className="flex items-center gap-1.5 text-soc-textMuted">
              <UserIcon className="w-3.5 h-3.5" />
              {user.email}
              <span className="ml-1 px-1.5 py-0.5 rounded bg-soc-panelAlt border border-soc-border text-2xs">
                {user.roles.join(", ")}
              </span>
            </span>
            <button onClick={handleLogout} className="btn !py-1 !px-2 text-xs">
              <LogOut className="w-3.5 h-3.5" /> Logout
            </button>
          </>
        ) : null}
      </div>
    </header>
  );
}