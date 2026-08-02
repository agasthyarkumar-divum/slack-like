import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import { api } from "@/lib/api/client";
import { tokenStorage } from "@/lib/storage/tokenStorage";
import type { NotificationPreference, Scope } from "@/lib/api/types";

type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  avatar_uri: string | null;
  status: string | null;
  notification_preference: NotificationPreference;
};

type AuthContextValue = {
  user: AuthUser | null;
  scope: Scope;
  isAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [scope, setScope] = useState<Scope>("users");
  const [isLoading, setIsLoading] = useState(true);

  async function loadCurrentUser() {
    try {
      const response = await api.get<AuthUser>("/users/me");
      setUser(response.data);
      setScope((response.headers["x-scope"] as Scope | undefined) ?? "users");
    } catch {
      setUser(null);
      setScope("users");
    }
  }

  useEffect(() => {
    (async () => {
      const accessToken = await tokenStorage.getAccessToken();
      if (accessToken) {
        await loadCurrentUser();
      }
      setIsLoading(false);
    })();
  }, []);

  async function login(email: string, password: string) {
    const response = await api.post("/auth/login", { email, password });
    await tokenStorage.setTokens(response.data.access_token, response.data.refresh_token);
    await loadCurrentUser();
  }

  async function register(email: string, password: string, displayName: string) {
    await api.post("/auth/register", { email, password, display_name: displayName });
    await login(email, password);
  }

  async function logout() {
    const refreshToken = await tokenStorage.getRefreshToken();
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch {
        // best-effort — clear local state regardless of whether this succeeded
      }
    }
    await tokenStorage.clear();
    setUser(null);
    setScope("users");
  }

  const isAdmin = scope === "admin" || scope === "superAdmin";

  const value = useMemo(
    () => ({ user, scope, isAdmin, isLoading, login, register, logout, refreshUser: loadCurrentUser }),
    [user, scope, isAdmin, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
