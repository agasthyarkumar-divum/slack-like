import { useRouter } from "expo-router";
import { Settings as SettingsIcon, Shield } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

export default function ProfileScreen() {
  const { user, isAdmin, logout } = useAuth();
  const { colors } = useTheme();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/workspace");
  }

  return (
    <Screen padded>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Profile</Text>
      </View>

      {user ? (
        <View style={styles.identity}>
          <Avatar name={user.display_name} imageUri={user.avatar_uri} size={72} />
          <Text style={[styles.name, { color: colors.textPrimary }]}>{user.display_name}</Text>
          <Text style={[styles.email, { color: colors.textSecondary }]}>{user.email}</Text>
          <View style={[styles.statusChip, { backgroundColor: colors.accentMossSoft }]}>
            <Text style={[styles.statusText, { color: colors.accentMoss }]}>{user.status ?? "offline"}</Text>
          </View>
        </View>
      ) : null}

      <View style={[styles.menu, { borderColor: colors.borderHairline }]}>
        <Pressable style={styles.menuRow} onPress={() => router.push("/settings")}>
          <SettingsIcon size={18} color={colors.textSecondary} strokeWidth={1.5} />
          <Text style={[styles.menuLabel, { color: colors.textPrimary }]}>Settings</Text>
        </Pressable>
        {isAdmin ? (
          <>
            <View style={[styles.menuSeparator, { backgroundColor: colors.borderHairline }]} />
            <Pressable style={styles.menuRow} onPress={() => router.push("/admin")}>
              <Shield size={18} color={colors.textSecondary} strokeWidth={1.5} />
              <Text style={[styles.menuLabel, { color: colors.textPrimary }]}>Admin Dashboard</Text>
            </Pressable>
          </>
        ) : null}
      </View>

      <View style={styles.logout}>
        <Button label="Log out" variant="danger" onPress={handleLogout} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { paddingTop: spacing.md },
  title: { fontFamily: fonts.display, fontSize: 28, marginBottom: spacing.lg },
  identity: { alignItems: "center", gap: spacing.xs, marginBottom: spacing.xl },
  name: { fontFamily: fonts.bodySemiBold, fontSize: 18, marginTop: spacing.sm },
  email: { fontFamily: fonts.body, fontSize: 14 },
  statusChip: { borderRadius: radii.pill, paddingHorizontal: spacing.sm + 2, paddingVertical: 4, marginTop: spacing.xs },
  statusText: { fontFamily: fonts.bodyMedium, fontSize: 12, textTransform: "capitalize" },
  menu: { borderWidth: 1, borderRadius: radii.md, overflow: "hidden" },
  menuRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md, paddingHorizontal: spacing.md },
  menuLabel: { fontFamily: fonts.bodyMedium, fontSize: 15 },
  menuSeparator: { height: 1 },
  logout: { marginTop: spacing.xl },
});
