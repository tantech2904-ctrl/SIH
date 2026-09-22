import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthContext } from "@/context/AuthContext";
import { Loading } from "@/components/Loading";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuthContext();
  const location = useLocation();

  // React to a global logout event (fired by api.ts on refresh failure,
  // or by useAuthContext's logout()) by causing a rerender that will
  // redirect via the conditional below.
  useEffect(() => {
    // No-op side effect; the redirect happens on the next render because
    // `user` becomes null and `loading` becomes false.
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-soc-bg">
        <Loading label="Checking session…" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}