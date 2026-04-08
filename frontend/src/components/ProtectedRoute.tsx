import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types";

export function ProtectedRoute({ allowedRole }: { allowedRole: UserRole }) {
  const { auth } = useAuth();

  if (!auth || auth.role !== allowedRole) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
