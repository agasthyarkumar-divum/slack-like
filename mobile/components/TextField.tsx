import { forwardRef } from "react";
import type { TextInputProps } from "react-native";
import { StyleSheet, Text, TextInput, View } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

type TextFieldProps = TextInputProps & {
  label?: string;
  error?: string;
};

export const TextField = forwardRef<TextInput, TextFieldProps>(function TextField(
  { label, error, style, ...inputProps },
  ref
) {
  const { colors } = useTheme();

  return (
    <View style={styles.container}>
      {label ? <Text style={[styles.label, { color: colors.textSecondary }]}>{label}</Text> : null}
      <TextInput
        ref={ref}
        placeholderTextColor={colors.textSecondary}
        style={[
          styles.input,
          {
            backgroundColor: colors.bgSurface,
            borderColor: error ? colors.stateError : colors.borderHairline,
            color: colors.textPrimary,
          },
          style,
        ]}
        {...inputProps}
      />
      {error ? <Text style={[styles.error, { color: colors.stateError }]}>{error}</Text> : null}
    </View>
  );
});

const styles = StyleSheet.create({
  container: { gap: spacing.xs },
  label: { fontFamily: fonts.bodyMedium, fontSize: 13 },
  input: {
    borderWidth: 1,
    borderRadius: radii.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    fontFamily: fonts.body,
    fontSize: 16,
  },
  error: { fontFamily: fonts.body, fontSize: 13 },
});
