import { StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, spacing } from "@/lib/theme/tokens";

type EmptyStateProps = {
  title: string;
  subtitle?: string;
};

// Short, direct, human copy — never corporate ("Get started by...").
export function EmptyState({ title, subtitle }: EmptyStateProps) {
  const { colors } = useTheme();
  return (
    <View style={styles.container}>
      <Text style={[styles.title, { color: colors.textPrimary }]}>{title}</Text>
      {subtitle ? <Text style={[styles.subtitle, { color: colors.textSecondary }]}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xxl, gap: spacing.sm },
  title: { fontFamily: fonts.display, fontSize: 20, textAlign: "center" },
  subtitle: { fontFamily: fonts.body, fontSize: 14, textAlign: "center" },
});
