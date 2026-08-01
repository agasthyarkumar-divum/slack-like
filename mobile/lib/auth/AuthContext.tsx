import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import { api } from "@/lib/api/client";
import { tokenStorage } from "@/lib/api/tokenStorage";

type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  avatar_uri: string | null;
  status: string | null;
};

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadCurrentUser() {
    try {
      const response = await api.get<AuthUser>("/users/me");
      setUser(response.data);
    } catch {
      setUser(null);
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
  }

  const value = useMemo(() => ({ user, isLoading, login, logout }), [user, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
