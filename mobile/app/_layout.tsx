import { Stack } from "expo-router";

// "/" resolves to (tabs)/index.tsx (Home). Phase 3 (auth) adds the redirect
// gate here that sends unauthenticated users to /login on launch.
export default function RootLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="login" />
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="channel/[id]" options={{ headerShown: true, title: "" }} />
      <Stack.Screen name="settings" options={{ headerShown: true, title: "Settings" }} />
      <Stack.Screen name="admin" options={{ headerShown: true, title: "Admin Dashboard" }} />
    </Stack>
  );
}
