import { Link, useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useAuth } from "@/lib/auth/AuthContext";

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>
      {user ? (
        <View style={styles.userInfo}>
          <Text style={styles.name}>{user.display_name}</Text>
          <Text style={styles.subtitle}>{user.email}</Text>
        </View>
      ) : null}
      <Text style={styles.subtitle}>
        Avatar, department/team, status setter land in Phase 10 (architecture.md §12).
      </Text>
      <Pressable style={styles.button} onPress={handleLogout}>
        <Text style={styles.buttonText}>Log out</Text>
      </Pressable>
      <Link href="/settings">Settings</Link>
      <Link href="/admin">Admin Dashboard</Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 8 },
  title: { fontSize: 20, fontWeight: "600" },
  userInfo: { alignItems: "center", marginBottom: 8 },
  name: { fontSize: 16, fontWeight: "600" },
  subtitle: { fontSize: 14, textAlign: "center" },
  button: {
    backgroundColor: "#a6503b",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 20,
    marginVertical: 8,
  },
  buttonText: { color: "#fff", fontSize: 14, fontWeight: "600" },
});
