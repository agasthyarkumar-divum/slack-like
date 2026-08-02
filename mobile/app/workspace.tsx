import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

// Divum Chat is single-workspace by design — this screen exists purely to
// match the familiar "pick a workspace" entry flow, with exactly one card.
export default function WorkspaceSwitcherScreen() {
  const { colors } = useTheme();
  const router = useRouter();

  return (
    <View style={[styles.container, { backgroundColor: colors.bgBase }]}>
      <View style={styles.stack}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Welcome back</Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Choose a workspace to continue.</Text>

        <Pressable
          onPress={() => router.push("/login")}
          style={({ pressed }) => [
            styles.card,
            { backgroundColor: colors.bgSurfaceRaised, borderColor: colors.borderHairline },
            pressed && styles.pressed,
          ]}
        >
          <View style={[styles.mark, { backgroundColor: colors.accentMossSoft }]}>
            <Text style={[styles.markText, { color: colors.accentMoss }]}>DC</Text>
          </View>
          <View style={styles.cardText}>
            <Text style={[styles.workspaceName, { color: colors.textPrimary }]}>Divum Chat</Text>
            <Text style={[styles.workspaceStatus, { color: colors.textSecondary }]}>All systems normal</Text>
          </View>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl },
  stack: { width: "100%", maxWidth: 380 },
  title: { fontFamily: fonts.display, fontSize: 30, marginBottom: spacing.xs },
  subtitle: { fontFamily: fonts.body, fontSize: 14, marginBottom: spacing.xl },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
  },
  pressed: { opacity: 0.85 },
  mark: {
    width: 44,
    height: 44,
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
  },
  markText: { fontFamily: fonts.display, fontSize: 16, fontWeight: "600" },
  cardText: { gap: 2 },
  workspaceName: { fontFamily: fonts.bodySemiBold, fontSize: 15 },
  workspaceStatus: { fontFamily: fonts.body, fontSize: 13 },
});
