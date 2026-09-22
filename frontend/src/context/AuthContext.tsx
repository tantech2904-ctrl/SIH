import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";
import { api, clearTokens, getAccessToken, setTokens } from "@/services/api";
import type { Me } from "@/types";

interface AuthState {
  user: Me | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initial load: if a token exists, try to fetch /me.
  useEffect(() => {
    let active = true;
    async function load() {
      if (!getAccessToken()) {
        if (active) {
          setUser(null);
          setLoading(false);
        }
        return;
      }
      try {
        const me = await api.me();
        if (active) {
          setUser(me);
          setLoading(false);
        }
      } catch {
        clearTokens();
        if (active) {
          setUser(null);
          setLoading(false);
        }
      }
    }
    load();

    const onLogout = () => {
      setUser(null);
      setLoading(false);
      setError(null);
    };
    window.addEventListener("ulpf:logout", onLogout);
    return () => {
      active = false;
      window.removeEventListener("ulpf:logout", onLogout);
    };
  }, []);

  // Cross-tab logout: when another tab clears the access token from
  // localStorage, the browser fires a `storage` event in this tab.
  // We clear our in-memory user state so ProtectedRoute redirects.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "ulpf.access_token" && e.newValue === null) {
        setUser(null);
        setError(null);
        setLoading(false);
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const t = await api.login(email, password);
      setTokens(t.access_token, t.refresh_token);
      const me = await api.me();
      setUser(me);
      setLoading(false);
      return true;
    } catch (e: any) {
      clearTokens();
      setUser(null);
      setError(e?.message || "Login failed");
      setLoading(false);
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* ignore — server-side logout is best-effort */
    }
    clearTokens();
    setUser(null);
    setError(null);
    window.dispatchEvent(new CustomEvent("ulpf:logout"));
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, login, logout }),
    [user, loading, error, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return ctx;
}