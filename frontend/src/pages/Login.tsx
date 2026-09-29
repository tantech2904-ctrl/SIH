import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  ShieldCheck,
  Loader2,
  Sparkles,
  UserCheck,
  Search,
  Scale,
  ArrowRight,
  Sun,
  Moon,
  Building2,
  UserPlus,
  LogIn,
} from "lucide-react";
import { RestartingBox } from "@/components/RestartingBox";
import { useTheme } from "@/context/ThemeContext";

interface DemoRole {
  id: "admin" | "team" | "analyst" | "auditor";
  name: string;
  role: string;
  email: string;
  pass: string;
  badge: string;
  badgeColor: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  recommended?: boolean;
}

const DEMO_ROLES: DemoRole[] = [
  {
    id: "admin",
    name: "Platform Administrator",
    role: "Admin (Full Access)",
    email: "admin@ulpf.local",
    pass: "ChangeMe_Admin123!",
    badge: "Recommended",
    badgeColor: "bg-amber-100 dark:bg-amber-500/15 text-amber-900 dark:text-amber-400 border-amber-300 dark:border-amber-500/30",
    description: "Complete unconstrained access: all 5 workspaces, correlation rules, attack simulation & cluster settings.",
    icon: ShieldCheck,
    recommended: true,
  },
  {
    id: "team",
    name: "Team BEETLES Workspace",
    role: "Tenant Lead",
    email: "team@ulpf.local",
    pass: "ChangeMe_Team123!",
    badge: "Isolated Team",
    badgeColor: "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-900 dark:text-emerald-400 border-emerald-300 dark:border-emerald-500/30",
    description: "Multi-tenant team workspace: private log streams, team incidents, connectors & isolated WORM evidence.",
    icon: Building2,
  },
  {
    id: "analyst",
    name: "SOC Triage Specialist",
    role: "Analyst",
    email: "analyst@ulpf.local",
    pass: "ChangeMe_Analyst123!",
    badge: "Investigation Role",
    badgeColor: "bg-sky-100 dark:bg-sky-500/15 text-sky-900 dark:text-sky-400 border-sky-300 dark:border-sky-500/30",
    description: "Real-time log streams, threat alert triage, MITRE ATT&CK exploration & query workbench.",
    icon: Search,
  },
  {
    id: "auditor",
    name: "Compliance & Forensics",
    role: "Auditor",
    email: "auditor@ulpf.local",
    pass: "ChangeMe_Auditor123!",
    badge: "Audit Role",
    badgeColor: "bg-purple-100 dark:bg-purple-500/15 text-purple-900 dark:text-purple-400 border-purple-300 dark:border-purple-500/30",
    description: "WORM cryptographic evidence preservation, SHA-256 ledger integrity verification & export.",
    icon: Scale,
  },
];

export default function Login() {
  const { login, register, loading, user } = useAuth();
  const { effectiveTheme, toggleTheme } = useTheme();
  const nav = useNavigate();
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("admin@ulpf.local");
  const [password, setPassword] = useState("ChangeMe_Admin123!");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regFullName, setRegFullName] = useState("");
  const [regWorkspaceName, setRegWorkspaceName] = useState("");
  const [regRole, setRegRole] = useState<"ADMIN" | "ANALYST" | "AUDITOR">("ADMIN");
  const [err, setErr] = useState<string | null>(null);
  const [restarting, setRestarting] = useState(
    sessionStorage.getItem("ulpf.restarting") === "true",
  );
  const [activeQuickRole, setActiveQuickRole] = useState<string | null>("admin");

  useEffect(() => {
    if (user) nav("/dashboard", { replace: true });
  }, [user, nav]);

  async function handleQuickLogin(role: DemoRole) {
    setActiveQuickRole(role.id);
    setEmail(role.email);
    setPassword(role.pass);
    setErr(null);
    const ok = await login(role.email, role.pass);
    if (ok) nav("/dashboard", { replace: true });
    else setErr(`Failed to authenticate as ${role.name}. Verify backend is running.`);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const ok = await login(email, password);
    if (ok) nav("/dashboard", { replace: true });
    else setErr("Invalid email or password");
  }

  async function onRegisterSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!regEmail || !regPassword) {
      setErr("Email and password are required");
      return;
    }
    const ok = await register({
      email: regEmail,
      password: regPassword,
      full_name: regFullName.trim() || undefined,
      workspace_name: regWorkspaceName.trim() || undefined,
      role: regRole,
    });
    if (ok) nav("/dashboard", { replace: true });
    else setErr("Registration failed. Please verify inputs or try another email.");
  }

  function onRestartReady() {
    sessionStorage.removeItem("ulpf.restarting");
    setRestarting(false);
  }

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-soc-bg px-4 py-8 relative selection:bg-soc-accent/25">
      {/* Top Floating Controls */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <button
          onClick={toggleTheme}
          type="button"
          aria-label="Toggle Theme"
          className="h-9 w-9 rounded-xl border border-soc-border bg-soc-panel/90 backdrop-blur-md flex items-center justify-center text-soc-text hover:border-soc-accent transition shadow-sm"
        >
          {effectiveTheme === "dark" ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-sky-500" />
          )}
        </button>
      </div>

      {restarting ? (
        <RestartingBox onReady={onRestartReady} />
      ) : (
        <div className="w-full max-w-4xl space-y-6">
          {/* Header Brand */}
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-soc-border bg-soc-panel shadow-sm text-xs font-semibold text-soc-textMuted mb-1">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>SIEM Unified Platform v0.1.0</span>
            </div>
            <div className="flex items-center justify-center gap-3">
              <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-soc-accent via-sky-500 to-indigo-600 flex items-center justify-center shadow-lg text-white font-black text-xl">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight text-soc-text">
                ULPF <span className="text-soc-accent">SecOps</span>
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-soc-textMuted max-w-md mx-auto">
              Unified Log Processing Framework & Security Operations Center
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* Left 7 Cols: 1-Click Judge & Demo Role Selection */}
            <div className="lg:col-span-7 flex flex-col justify-between rounded-2xl border border-soc-border bg-soc-panel/95 backdrop-blur-md p-5 sm:p-6 shadow-md transition-all">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-amber-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-soc-text">
                      Quick Demo Access (1-Click Login)
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-soc-textDim">
                    Instant Auth
                  </span>
                </div>
                <p className="text-xs text-soc-textMuted mb-2.5 leading-relaxed">
                  Judges and evaluators can instantly simulate enterprise personas or isolated team sandboxes.
                </p>
                <div className="mb-3.5 p-2.5 rounded-xl border border-soc-accent/25 bg-soc-accent/5 text-[11px] text-soc-text leading-relaxed flex items-start gap-2">
                  <Building2 className="h-4 w-4 text-soc-accent shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-soc-accent font-semibold">Multi-Tenancy & Teams:</strong> Select <span className="font-semibold text-emerald-500">Team BEETLES</span> below to explore an isolated team sandbox, or create/join any team workspace using the tab on the right.
                  </div>
                </div>

                {/* Role Cards List */}
                <div className="space-y-3">
                  {DEMO_ROLES.map((role) => {
                    const RoleIcon = role.icon;
                    const isSelected = activeQuickRole === role.id;
                    return (
                      <button
                        key={role.id}
                        type="button"
                        onClick={() => handleQuickLogin(role)}
                        disabled={loading}
                        className={`w-full text-left rounded-xl p-3.5 transition-all duration-200 border flex items-start gap-3.5 relative group ${
                          role.recommended
                            ? isSelected
                              ? "bg-soc-accent/10 border-soc-accent shadow-md"
                              : "bg-soc-panelAlt/50 border-soc-border hover:border-soc-accent/60"
                            : isSelected
                            ? "bg-soc-accent/10 border-soc-accent shadow-sm"
                            : "bg-soc-panelAlt/30 border-soc-border hover:border-soc-borderStrong"
                        }`}
                      >
                        <div
                          className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                            role.recommended
                              ? "bg-gradient-to-br from-amber-500 to-soc-accent text-white shadow-sm"
                              : "bg-soc-panelAlt border border-soc-border text-soc-text group-hover:text-soc-accent"
                          }`}
                        >
                          <RoleIcon className="h-4 w-4" />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-bold text-soc-text truncate">
                              {role.name}
                            </span>
                            <span
                              className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border shrink-0 ${role.badgeColor}`}
                            >
                              {role.badge}
                            </span>
                          </div>
                          <p className="text-[11px] text-soc-textMuted mt-1 line-clamp-2">
                            {role.description}
                          </p>
                          <div className="mt-2 flex items-center gap-2 text-[10px] font-mono text-soc-textDim">
                            <span>{role.email}</span>
                          </div>
                        </div>

                        <div className="self-center">
                          <ArrowRight className="h-4 w-4 text-soc-textDim group-hover:text-soc-accent group-hover:translate-x-0.5 transition-all" />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-soc-border text-[11px] text-soc-textDim flex items-center gap-2">
                <UserCheck className="h-3.5 w-3.5 text-emerald-500" />
                <span>Pre-configured with zero friction. Click any role to enter.</span>
              </div>
            </div>

            {/* Right 5 Cols: Standard Credentials Form or Isolated Workspace Registration */}
            <div className="lg:col-span-5 rounded-2xl border border-soc-border bg-soc-panel/95 backdrop-blur-md p-5 sm:p-6 shadow-md flex flex-col justify-between">
              <div>
                {/* Tab Switcher */}
                <div className="flex rounded-xl bg-soc-panelAlt p-1 border border-soc-border mb-4">
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMode("login");
                      setErr(null);
                    }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                      authMode === "login"
                        ? "bg-soc-panel text-soc-text shadow-sm border border-soc-border"
                        : "text-soc-textDim hover:text-soc-text"
                    }`}
                  >
                    <LogIn className="h-3.5 w-3.5" />
                    <span>Log In</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMode("register");
                      setErr(null);
                    }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                      authMode === "register"
                        ? "bg-soc-panel text-soc-accent shadow-sm border border-soc-border"
                        : "text-soc-textDim hover:text-soc-text"
                    }`}
                  >
                    <Building2 className="h-3.5 w-3.5" />
                    <span>New Workspace</span>
                  </button>
                </div>

                {authMode === "login" ? (
                  <form onSubmit={onSubmit} className="space-y-4">
                    <div>
                      <h3 className="text-sm font-bold text-soc-text">
                        Manual Log In
                      </h3>
                      <p className="text-xs text-soc-textMuted mt-0.5">
                        Log in with custom security credentials
                      </p>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <label className="label">Account Email</label>
                        <input
                          className="input rounded-xl"
                          type="email"
                          value={email}
                          onChange={(e) => {
                            setEmail(e.target.value);
                            setActiveQuickRole(null);
                          }}
                          autoComplete="username"
                          required
                        />
                      </div>

                      <div>
                        <label className="label">Password</label>
                        <input
                          className="input rounded-xl"
                          type="password"
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            setActiveQuickRole(null);
                          }}
                          autoComplete="current-password"
                          required
                        />
                      </div>
                    </div>

                    {err && (
                      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-500 font-medium leading-relaxed">
                        {err}
                      </div>
                    )}

                    <button
                      type="submit"
                      className="btn btn-primary w-full justify-center rounded-xl py-2.5 font-semibold text-sm shadow-md"
                      disabled={loading}
                    >
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Authenticating...</span>
                        </span>
                      ) : (
                        <span>Log In to Platform</span>
                      )}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={onRegisterSubmit} className="space-y-3">
                    <div>
                      <h3 className="text-sm font-bold text-soc-text">
                        Create or Join Workspace
                      </h3>
                      <p className="text-[11px] text-soc-textMuted mt-0.5">
                        Spin up a new private sandbox or enter an existing team name to collaborate
                      </p>
                    </div>

                    <div>
                      <label className="label text-[11px]">Workspace / Team Name</label>
                      <input
                        className="input rounded-xl text-xs py-1.5"
                        type="text"
                        placeholder="e.g. Team BEETLES or RedTeam Alpha"
                        value={regWorkspaceName}
                        onChange={(e) => setRegWorkspaceName(e.target.value)}
                      />
                      <p className="text-[10px] text-soc-textDim mt-1">
                        💡 If the team name already exists, you will automatically join that team!
                      </p>
                    </div>

                    <div>
                      <label className="label text-[11px]">Workspace Role</label>
                      <div className="grid grid-cols-3 gap-1.5 mt-1">
                        <button
                          type="button"
                          onClick={() => setRegRole("ADMIN")}
                          className={`py-1.5 px-2 rounded-xl text-xs font-semibold border text-center transition ${
                            regRole === "ADMIN"
                              ? "bg-soc-accent/15 border-soc-accent text-soc-accent shadow-sm"
                              : "bg-soc-panelAlt border-soc-border text-soc-textMuted hover:border-soc-accent/40"
                          }`}
                        >
                          Admin
                        </button>
                        <button
                          type="button"
                          onClick={() => setRegRole("ANALYST")}
                          className={`py-1.5 px-2 rounded-xl text-xs font-semibold border text-center transition ${
                            regRole === "ANALYST"
                              ? "bg-sky-500/15 border-sky-500 text-sky-400 shadow-sm"
                              : "bg-soc-panelAlt border-soc-border text-soc-textMuted hover:border-sky-500/40"
                          }`}
                        >
                          Analyst
                        </button>
                        <button
                          type="button"
                          onClick={() => setRegRole("AUDITOR")}
                          className={`py-1.5 px-2 rounded-xl text-xs font-semibold border text-center transition ${
                            regRole === "AUDITOR"
                              ? "bg-purple-500/15 border-purple-500 text-purple-400 shadow-sm"
                              : "bg-soc-panelAlt border-soc-border text-soc-textMuted hover:border-purple-500/40"
                          }`}
                        >
                          Auditor
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="label text-[11px]">Full Name</label>
                      <input
                        className="input rounded-xl text-xs py-1.5"
                        type="text"
                        placeholder="e.g. Lead Analyst"
                        value={regFullName}
                        onChange={(e) => setRegFullName(e.target.value)}
                      />
                    </div>

                    <div>
                      <label className="label text-[11px]">Work Email</label>
                      <input
                        className="input rounded-xl text-xs py-1.5"
                        type="email"
                        placeholder="analyst@domain.com"
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        autoComplete="username"
                        required
                      />
                    </div>

                    <div>
                      <label className="label text-[11px]">Password</label>
                      <input
                        className="input rounded-xl text-xs py-1.5"
                        type="password"
                        placeholder="Min 8 characters"
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        autoComplete="new-password"
                        required
                      />
                    </div>

                    {err && (
                      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-2.5 text-xs text-red-500 font-medium leading-relaxed">
                        {err}
                      </div>
                    )}

                    <button
                      type="submit"
                      className="btn btn-primary w-full justify-center rounded-xl py-2.5 font-semibold text-xs shadow-md mt-1"
                      disabled={loading}
                    >
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Setting Up Workspace...</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5">
                          <UserPlus className="h-3.5 w-3.5" />
                          <span>Create or Join Team Workspace</span>
                        </span>
                      )}
                    </button>
                  </form>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-soc-border text-center text-[10px] text-soc-textDim">
                {authMode === "register"
                  ? "Teams with matching names share private telemetry, alerts, and incidents."
                  : "Role-Based Access Control (RBAC) enforced across all endpoints."}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}