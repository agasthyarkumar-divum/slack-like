import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { PropsWithChildren } from "react";

import { useAuth } from "@/lib/auth/AuthContext";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import MainWorkspace from "@/pages/MainWorkspace";
import Signup from "@/pages/Signup";

const PUBLIC_ONLY_PATHS = new Set(["/login", "/signup"]);

function AuthGate({ children }: PropsWithChildren) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return null;
  if (user && PUBLIC_ONLY_PATHS.has(location.pathname)) return <Navigate to="/" replace />;

  return <>{children}</>;
}

export default function App() {
  const { user } = useAuth();

  return (
    <AuthGate>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={user ? <MainWorkspace /> : <Home />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthGate>
  );
}
