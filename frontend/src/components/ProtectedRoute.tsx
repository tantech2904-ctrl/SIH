import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Loading } from "./Loading";

export function ProtectedRoute({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: string[];
}) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading label="Checking session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.some((r) => user.roles.includes(r))) {
    return (
      <div className="p-6">
        <div className="panel p-4 text-red-300 border-red-500/40">
          You do not have permission to view this page.
        </div>
      </div>
    );
  }
  return <>{children}</>;
}