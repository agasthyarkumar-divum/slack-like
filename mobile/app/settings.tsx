import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Check } from "lucide-react-native";

import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { updateSettings } from "@/lib/api/users";
import type { NotificationPreference } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import type { ThemeMode } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

const APPEARANCE_MODES: { value: ThemeMode; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

const NOTIFICATION_OPTIONS: { value: NotificationPreference; label: string; description: string }[] = [
  { value: "all", label: "All", description: "Every mention, DM, and reaction." },
  { value: "mentions_dms", label: "Mentions & DMs", description: "Skip reaction notifications." },
  { value: "none", label: "Nothing", description: "Turn off in-app notifications." },
];

export default function SettingsScreen() {
  const { colors, mode, setMode } = useTheme();
  const { user, logout, refreshUser } = useAuth();
  const router = useRouter();
  const [preference, setPreference] = useState<NotificationPreference>(user?.notification_preference ?? "all");
  const [isSaving, setIsSaving] = useState(false);

  async function handleLogout() {
    await logout();
    router.replace("/workspace");
  }

  async function handlePreferenceChange(next: NotificationPreference) {
    setPreference(next);
    setIsSaving(true);
    try {
      await updateSettings(next);
      await refreshUser();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Screen padded>
      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Appearance</Text>
      <View style={[styles.segmented, { borderColor: colors.borderHairline }]}>
        {APPEARANCE_MODES.map((option) => {
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

      <Text style={[styles.sectionLabel, { color: colors.textSecondary, marginTop: spacing.xl }]}>Notifications</Text>
      <View style={[styles.radioGroup, { borderColor: colors.borderHairline }]}>
        {NOTIFICATION_OPTIONS.map((option, index) => {
          const isActive = option.value === preference;
          return (
            <Pressable
              key={option.value}
              onPress={() => handlePreferenceChange(option.value)}
              disabled={isSaving}
              style={[
                styles.radioRow,
                index < NOTIFICATION_OPTIONS.length - 1 && { borderBottomWidth: 1, borderBottomColor: colors.borderHairline },
              ]}
            >
              <View style={[styles.radioCircle, { borderColor: isActive ? colors.accentMoss : colors.borderHairline }]}>
                {isActive ? <Check size={12} color={colors.accentMoss} strokeWidth={3} /> : null}
              </View>
              <View style={styles.radioText}>
                <Text style={[styles.radioLabel, { color: colors.textPrimary }]}>{option.label}</Text>
                <Text style={[styles.radioDescription, { color: colors.textSecondary }]}>{option.description}</Text>
              </View>
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
  radioGroup: { borderWidth: 1, borderRadius: radii.md, overflow: "hidden" },
  radioRow: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm, padding: spacing.md },
  radioCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
  },
  radioText: { flex: 1, gap: 2 },
  radioLabel: { fontFamily: fonts.bodyMedium, fontSize: 14 },
  radioDescription: { fontFamily: fonts.body, fontSize: 12 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: spacing.md, borderBottomWidth: 1 },
  infoLabel: { fontFamily: fonts.body, fontSize: 14 },
  infoValue: { fontFamily: fonts.body, fontSize: 14 },
  logout: { marginTop: spacing.xxl },
});
