import axios from "axios";

import { tokenStorage } from "@/lib/api/tokenStorage";

// EXPO_PUBLIC_-prefixed vars are inlined at build time (see mobile/.env.example).
// localhost works for the iOS simulator and the web preview; a physical device
// needs the host machine's LAN IP instead.
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use(async (config) => {
  const token = await tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Dedupe concurrent refreshes — if five requests 401 at once, only one
// /auth/refresh call should fire; the rest wait on the same promise.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = await tokenStorage.getRefreshToken();
  if (!refreshToken) return null;

  const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
    refresh_token: refreshToken,
  });
  await tokenStorage.setTokens(response.data.access_token, response.data.refresh_token);
  return response.data.access_token as string;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint = originalRequest?.url?.startsWith("/auth/");

    if (error.response?.status !== 401 || originalRequest._retry || isAuthEndpoint) {
      return Promise.reject(error);
    }
    originalRequest._retry = true;

    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const newAccessToken = await refreshPromise;
      if (!newAccessToken) throw error;

      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      await tokenStorage.clear();
      return Promise.reject(refreshError);
    }
  }
);
