import { Link } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

export default function ProfileScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>
      <Text style={styles.subtitle}>
        Avatar, department/team, status setter land in Phase 3 (architecture.md §12).
      </Text>
      <Link href="/settings">Settings</Link>
      <Link href="/admin">Admin Dashboard</Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 8 },
  title: { fontSize: 20, fontWeight: "600" },
  subtitle: { fontSize: 14, textAlign: "center" },
});
