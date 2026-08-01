import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

type ButtonVariant = "primary" | "outline" | "danger";

type ButtonProps = {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  loading?: boolean;
  disabled?: boolean;
};

export function Button({ label, onPress, variant = "primary", loading, disabled }: ButtonProps) {
  const { colors } = useTheme();
  const [isFocused, setIsFocused] = useState(false);
  const isDisabled = disabled || loading;

  const backgroundColor =
    variant === "primary" ? colors.accentMoss : variant === "danger" ? colors.stateError : "transparent";
  const borderColor = variant === "outline" ? colors.borderHairline : "transparent";
  const textColor = variant === "outline" ? colors.textPrimary : "#FFFFFF";

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled }}
      onPress={onPress}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        { backgroundColor, borderColor, borderWidth: variant === "outline" ? 1 : 0 },
        isDisabled && styles.disabled,
        pressed && styles.pressed,
        isFocused && [styles.focused, { borderColor: colors.accentMoss }],
      ]}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <Text style={[styles.label, { color: textColor }]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: radii.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    alignItems: "center",
    justifyContent: "center",
  },
  disabled: { opacity: 0.5 },
  pressed: { opacity: 0.85 },
  focused: { borderWidth: 2 },
  label: { fontFamily: fonts.bodySemiBold, fontSize: 15 },
});
