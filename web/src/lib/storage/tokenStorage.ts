// localStorage counterpart of mobile/lib/api/tokenStorage.ts (which wraps
// SecureStore/AsyncStorage) — same key names, so a token issued to one
// client is meaningless to read from the other's storage anyway (different
// origins), but keeping the naming convention shared avoids confusion.
const ACCESS_TOKEN_KEY = "divum_chat_access_token";
const REFRESH_TOKEN_KEY = "divum_chat_refresh_token";

export const tokenStorage = {
  getAccessToken: async () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: async () => localStorage.getItem(REFRESH_TOKEN_KEY),
  async setTokens(accessToken: string, refreshToken: string) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  async clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
