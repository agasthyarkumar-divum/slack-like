import { Link } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

export default function HomeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Home</Text>
      <Text style={styles.subtitle}>
        Channel / DM list lands in Phase 5 (architecture.md §6, §12).
      </Text>
      <Link href="/channel/general">Open #general (placeholder)</Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 8 },
  title: { fontSize: 20, fontWeight: "600" },
  subtitle: { fontSize: 14, textAlign: "center" },
});
