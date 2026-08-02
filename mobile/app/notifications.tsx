import { useNavigation, useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";

import { EmptyState } from "@/components/EmptyState";
import { Screen } from "@/components/Screen";
import { listNotifications, markAllRead, markRead } from "@/lib/api/notifications";
import type { Notification } from "@/lib/api/types";
import { useNotifications } from "@/lib/notifications/NotificationsContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";
import { useWS } from "@/lib/ws/WSContext";

function describe(notification: Notification): string {
  const payload = notification.payload as { preview?: string; emoji?: string };
  if (notification.type === "mention") return `Mentioned you: “${payload.preview ?? ""}”`;
  if (notification.type === "dm") return payload.preview ?? "New direct message";
  if (notification.type === "reaction") return `Reacted ${payload.emoji ?? ""} to your message`;
  return "New notification";
}

function timeLabel(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function NotificationsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const navigation = useNavigation();
  const { subscribe } = useWS();
  const { unreadCount, refresh: refreshUnreadCount } = useNotifications();
  const [items, setItems] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const unreadCountRef = useRef(unreadCount);
  unreadCountRef.current = unreadCount;

  const load = useCallback(async () => {
    const data = await listNotifications();
    setItems(data.items);
  }, []);

  useEffect(() => {
    load().finally(() => setIsLoading(false));
  }, [load]);

  useEffect(() => subscribe("notification.new", () => load()), [subscribe, load]);

  // Tab screens stay mounted when you switch away and back — a mount-only
  // effect only fires the very first time you visit the tab, so opening
  // Notifications a second time (after a new one arrived) wouldn't clear the
  // badge. A navigation focus listener fires on every visit, mount or not.
  useEffect(() => {
    const unsubscribeFocus = navigation.addListener("focus", async () => {
      await load();
      if (unreadCountRef.current > 0) {
        await markAllRead();
        setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
        await refreshUnreadCount();
      }
    });
    return unsubscribeFocus;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigation, load]);

  async function handleRefresh() {
    setIsRefreshing(true);
    await Promise.all([load(), refreshUnreadCount()]);
    setIsRefreshing(false);
  }

  async function handlePress(notification: Notification) {
    if (!notification.is_read) {
      await markRead(notification.id);
      setItems((prev) => prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n)));
      await refreshUnreadCount();
    }
    const channelId = (notification.payload as { channel_id?: string }).channel_id;
    if (channelId) router.push(`/channel/${channelId}`);
  }

  async function handleMarkAllRead() {
    await markAllRead();
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    await refreshUnreadCount();
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Notifications</Text>
        {unreadCount > 0 ? (
          <Pressable onPress={handleMarkAllRead}>
            <Text style={[styles.markAllRead, { color: colors.accentMoss }]}>Mark all read</Text>
          </Pressable>
        ) : null}
      </View>

      {isLoading ? (
        <ActivityIndicator style={styles.loading} color={colors.accentMoss} />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} tintColor={colors.accentMoss} />}
          ListEmptyComponent={<EmptyState title="No notifications yet." subtitle="Mentions and replies will show up here." />}
          ItemSeparatorComponent={() => <View style={[styles.separator, { backgroundColor: colors.borderHairline }]} />}
          renderItem={({ item }) => (
            <Pressable onPress={() => handlePress(item)} style={styles.row}>
              {!item.is_read ? <View style={[styles.unreadDot, { backgroundColor: colors.accentMoss }]} /> : <View style={styles.unreadDotPlaceholder} />}
              <View style={styles.rowText}>
                <Text style={[styles.rowDescription, { color: colors.textPrimary }]} numberOfLines={2}>
                  {describe(item)}
                </Text>
                <Text style={[styles.rowTime, { color: colors.textSecondary }]}>{timeLabel(item.created_at)}</Text>
              </View>
            </Pressable>
          )}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  title: { fontFamily: fonts.display, fontSize: 28 },
  markAllRead: { fontFamily: fonts.bodyMedium, fontSize: 13 },
  loading: { marginTop: spacing.xxl },
  row: { flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, alignItems: "flex-start" },
  unreadDot: { width: 8, height: 8, borderRadius: radii.pill, marginTop: 6 },
  unreadDotPlaceholder: { width: 8, height: 8, marginTop: 6 },
  rowText: { flex: 1, gap: 2 },
  rowDescription: { fontFamily: fonts.body, fontSize: 14, lineHeight: 20 },
  rowTime: { fontFamily: fonts.body, fontSize: 12 },
  separator: { height: 1, marginLeft: spacing.lg + 8 + spacing.sm },
});
