import { deleteItem, getItem, setItem } from "@/lib/storage/platformStorage";

const ACCESS_TOKEN_KEY = "divum_chat_access_token";
const REFRESH_TOKEN_KEY = "divum_chat_refresh_token";

export const tokenStorage = {
  getAccessToken: () => getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => getItem(REFRESH_TOKEN_KEY),
  async setTokens(accessToken: string, refreshToken: string) {
    await Promise.all([
      setItem(ACCESS_TOKEN_KEY, accessToken),
      setItem(REFRESH_TOKEN_KEY, refreshToken),
    ]);
  },
  async clear() {
    await Promise.all([deleteItem(ACCESS_TOKEN_KEY), deleteItem(REFRESH_TOKEN_KEY)]);
  },
};
