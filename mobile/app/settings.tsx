import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

const MODES: { value: "system" | "light" | "dark"; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

export default function SettingsScreen() {
  const { colors, mode, setMode } = useTheme();
  const { logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <Screen padded>
      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Appearance</Text>
      <View style={[styles.segmented, { borderColor: colors.borderHairline }]}>
        {MODES.map((option) => {
          const isActive = option.value === mode;
          return (
            <Pressable
              key={option.value}
              onPress={() => setMode(option.value)}
              style={[styles.segment, isActive && { backgroundColor: colors.accentMossSoft }]}
            >
              <Text style={[styles.segmentLabel, { color: isActive ? colors.accentMoss : colors.textSecondary }]}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={[styles.sectionLabel, { color: colors.textSecondary, marginTop: spacing.xl }]}>About</Text>
      <View style={[styles.infoRow, { borderColor: colors.borderHairline }]}>
        <Text style={[styles.infoLabel, { color: colors.textPrimary }]}>Version</Text>
        <Text style={[styles.infoValue, { color: colors.textSecondary }]}>0.1.0</Text>
      </View>

      <View style={styles.logout}>
        <Button label="Log out" variant="danger" onPress={handleLogout} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  sectionLabel: { fontFamily: fonts.bodyMedium, fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: spacing.sm, marginTop: spacing.lg },
  segmented: { flexDirection: "row", borderWidth: 1, borderRadius: radii.md, overflow: "hidden" },
  segment: { flex: 1, paddingVertical: spacing.sm + 2, alignItems: "center" },
  segmentLabel: { fontFamily: fonts.bodyMedium, fontSize: 14 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: spacing.md, borderBottomWidth: 1 },
  infoLabel: { fontFamily: fonts.body, fontSize: 14 },
  infoValue: { fontFamily: fonts.body, fontSize: 14 },
  logout: { marginTop: spacing.xxl },
});
