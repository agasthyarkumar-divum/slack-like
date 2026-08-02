import { useRouter } from "expo-router";
import { Bell, Moon, Search, Settings, Sun } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { ChannelList } from "@/components/ChannelList";
import { HeaderIconButton } from "@/components/HeaderIconButton";
import { Screen } from "@/components/Screen";
import { useAuth } from "@/lib/auth/AuthContext";
import { useNotifications } from "@/lib/notifications/NotificationsContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, spacing } from "@/lib/theme/tokens";

export default function HomeScreen() {
  const { colors, isDark, toggle } = useTheme();
  const { user } = useAuth();
  const { unreadCount } = useNotifications();
  const router = useRouter();

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Divum Chat</Text>
        <View style={styles.headerActions}>
          <HeaderIconButton accessibilityLabel="Toggle theme" onPress={toggle}>
            {isDark ? (
              <Sun size={18} color={colors.textSecondary} strokeWidth={1.5} />
            ) : (
              <Moon size={18} color={colors.textSecondary} strokeWidth={1.5} />
            )}
          </HeaderIconButton>
          <HeaderIconButton accessibilityLabel="Search" onPress={() => router.push("/search")}>
            <Search size={18} color={colors.textSecondary} strokeWidth={1.5} />
          </HeaderIconButton>
          <HeaderIconButton accessibilityLabel="Settings" onPress={() => router.push("/settings")}>
            <Settings size={18} color={colors.textSecondary} strokeWidth={1.5} />
          </HeaderIconButton>
        </View>
      </View>

      <ChannelList onSelect={(channel) => router.push(`/channel/${channel.id}`)} />

      <Pressable
        style={[styles.footer, { borderTopColor: colors.borderHairline }]}
        onPress={() => router.push("/profile")}
      >
        <Avatar name={user?.display_name ?? "?"} imageUri={user?.avatar_uri} size={32} />
        <Text style={[styles.userName, { color: colors.textPrimary }]} numberOfLines={1}>
          {user?.display_name}
        </Text>
        <HeaderIconButton
          accessibilityLabel="Notifications"
          badgeCount={unreadCount}
          onPress={() => router.push("/notifications")}
        >
          <Bell size={18} color={colors.textSecondary} strokeWidth={1.5} />
        </HeaderIconButton>
      </Pressable>
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
  title: { fontFamily: fonts.display, fontSize: 26 },
  headerActions: { flexDirection: "row", gap: spacing.xs },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    padding: spacing.md,
    borderTopWidth: 1,
  },
  userName: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14 },
});
