import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { PropsWithChildren } from "react";

import { useAuth } from "@/lib/auth/AuthContext";
import Login from "@/pages/Login";
import MainWorkspace from "@/pages/MainWorkspace";
import WorkspaceSwitcher from "@/pages/WorkspaceSwitcher";

const PUBLIC_PATHS = new Set(["/workspace", "/login"]);

function AuthGate({ children }: PropsWithChildren) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return null;

  const onPublicPath = PUBLIC_PATHS.has(location.pathname);
  if (!user && !onPublicPath) return <Navigate to="/workspace" replace />;
  if (user && onPublicPath) return <Navigate to="/" replace />;

  return <>{children}</>;
}

export default function App() {
  return (
    <AuthGate>
      <Routes>
        <Route path="/workspace" element={<WorkspaceSwitcher />} />
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<MainWorkspace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthGate>
  );
}
