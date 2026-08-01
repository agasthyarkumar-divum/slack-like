import type { PropsWithChildren } from "react";
import type { StyleProp, ViewStyle } from "react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useTheme } from "@/lib/theme/ThemeContext";

type ScreenProps = PropsWithChildren<{ style?: StyleProp<ViewStyle>; padded?: boolean }>;

export function Screen({ children, style, padded = false }: ScreenProps) {
  const { colors } = useTheme();
  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: colors.bgBase }]} edges={["top", "bottom"]}>
      <View style={[styles.container, padded && styles.padded, style]}>{children}</View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  container: { flex: 1 },
  padded: { paddingHorizontal: 20 },
});
