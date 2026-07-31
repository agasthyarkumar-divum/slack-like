import { StyleSheet, Text, View } from "react-native";

type PlaceholderScreenProps = {
  title: string;
  subtitle?: string;
};

/**
 * Stand-in for screens not yet built out (Phase 10 wires the real design
 * system per architecture.md §12). Exists so the navigation shape can be
 * exercised end-to-end before any screen has real content.
 */
export function PlaceholderScreen({ title, subtitle }: PlaceholderScreenProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: "600",
  },
  subtitle: {
    fontSize: 14,
    textAlign: "center",
  },
});
