import * as Notifications from "expo-notifications";
import { createContext, useContext, useEffect, useState } from "react";
import type { PropsWithChildren } from "react";
import { Platform } from "react-native";

import { listNotifications } from "@/lib/api/notifications";
import { useAuth } from "@/lib/auth/AuthContext";
import { useWS } from "@/lib/ws/WSContext";

type NotificationsContextValue = {
  unreadCount: number;
  refresh: () => Promise<void>;
};

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

// Setting the app icon badge count is a *local* action — it only reflects
// what this running app instance already knows. It updates correctly while
// the app is open or recently backgrounded, but NOT while fully closed,
// since that would need a real push notification (silent APNs/FCM push) to
// wake the OS and update it — the backend's FCM integration is still a stub
// (architecture.md §9), so that half doesn't exist yet.
async function setAppBadge(count: number) {
  if (Platform.OS === "web") return; // unsupported on web, no-op there anyway
  try {
    await Notifications.setBadgeCountAsync(count);
  } catch {
    // best-effort — a missing badge isn't worth surfacing an error over
  }
}

export function NotificationsProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const { subscribe } = useWS();
  const [unreadCount, setUnreadCount] = useState(0);

  async function refresh() {
    if (!user) return;
    const data = await listNotifications();
    setUnreadCount(data.unread_count);
  }

  useEffect(() => {
    if (Platform.OS === "web") return;
    Notifications.requestPermissionsAsync().catch(() => {});
  }, []);

  useEffect(() => {
    if (user) refresh();
    else setUnreadCount(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  useEffect(() => subscribe("notification.new", () => refresh()), [subscribe]);

  useEffect(() => {
    setAppBadge(unreadCount);
  }, [unreadCount]);

  return (
    <NotificationsContext.Provider value={{ unreadCount, refresh }}>{children}</NotificationsContext.Provider>
  );
}

export function useNotifications(): NotificationsContextValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error("useNotifications must be used within a NotificationsProvider");
  return ctx;
}
