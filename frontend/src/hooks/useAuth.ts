import { useEffect, useState } from "react";
import { api, clearTokens, getAccessToken, setTokens } from "@/services/api";
import type { Me } from "@/types";

interface AuthState {
  user: Me | null;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let active = true;
    async function load() {
      if (!getAccessToken()) {
        setState({ user: null, loading: false, error: null });
        return;
      }
      try {
        const me = await api.me();
        if (active) setState({ user: me, loading: false, error: null });
      } catch {
        if (active) setState({ user: null, loading: false, error: null });
      }
    }
    load();
    const onLogout = () => setState({ user: null, loading: false, error: null });
    window.addEventListener("ulpf:logout", onLogout);
    return () => {
      active = false;
      window.removeEventListener("ulpf:logout", onLogout);
    };
  }, []);

  async function login(email: string, password: string) {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const t = await api.login(email, password);
      setTokens(t.access_token, t.refresh_token);
      const me = await api.me();
      setState({ user: me, loading: false, error: null });
      return true;
    } catch (e: any) {
      setState({ user: null, loading: false, error: e.message || "Login failed" });
      return false;
    }
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      /* ignore */
    }
    clearTokens();
    setState({ user: null, loading: false, error: null });
  }

  return { ...state, login, logout };
}