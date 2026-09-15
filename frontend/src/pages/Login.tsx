import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { ShieldCheck, Loader2 } from "lucide-react";

export default function Login() {
  const { login, loading } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("admin@ulpf.local");
  const [password, setPassword] = useState("ChangeMe_Admin123!");
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const ok = await login(email, password);
    if (ok) nav("/dashboard");
    else setErr("Invalid credentials");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-soc-bg px-4">
      <form onSubmit={onSubmit} className="panel p-6 w-full max-w-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-soc-accent to-soc-accentDim flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="text-sm font-bold">ULPF</div>
            <div className="text-2xs text-soc-textDim">Sign in to continue</div>
          </div>
        </div>
        <div className="mb-3">
          <label className="label">Email</label>
          <input
            className="input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
        </div>
        <div className="mb-3">
          <label className="label">Password</label>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        {err ? <div className="text-xs text-red-400 mb-3">{err}</div> : null}
        <button className="btn btn-primary w-full justify-center" disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign in"}
        </button>
        <div className="text-2xs text-soc-textDim mt-4 leading-relaxed">
          Default credentials are bootstrapped on first startup. Change them immediately.
        </div>
      </form>
    </div>
  );
}