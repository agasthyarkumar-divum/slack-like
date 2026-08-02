import type { ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii } from "@/lib/theme/tokens";

type HeaderIconButtonProps = {
  onPress: () => void;
  accessibilityLabel: string;
  children: ReactNode;
  badgeCount?: number;
};

export function HeaderIconButton({ onPress, accessibilityLabel, children, badgeCount }: HeaderIconButtonProps) {
  const { colors } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={({ pressed }) => [styles.button, pressed && { backgroundColor: colors.bgSurface }]}
    >
      {children}
      {badgeCount ? (
        <View style={[styles.badge, { backgroundColor: colors.accentMoss }]}>
          <Text style={styles.badgeText}>{badgeCount > 9 ? "9+" : badgeCount}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 36,
    height: 36,
    borderRadius: radii.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  badge: {
    position: "absolute",
    top: 2,
    right: 2,
    minWidth: 16,
    height: 16,
    borderRadius: radii.pill,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 3,
  },
  badgeText: { color: "#FFF", fontFamily: fonts.bodySemiBold, fontSize: 9 },
});
