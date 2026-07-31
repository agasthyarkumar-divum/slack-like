import { Redirect, Stack, usePathname } from "expo-router";
import type { PropsWithChildren } from "react";

import { AuthProvider, useAuth } from "@/lib/auth/AuthContext";

function AuthGate({ children }: PropsWithChildren) {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();

  if (isLoading) return null;

  const isOnLoginScreen = pathname === "/login";
  if (!user && !isOnLoginScreen) return <Redirect href="/login" />;
  if (user && isOnLoginScreen) return <Redirect href="/" />;

  return <>{children}</>;
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <AuthGate>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="login" />
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="channel/[id]" options={{ headerShown: true, title: "" }} />
          <Stack.Screen name="settings" options={{ headerShown: true, title: "Settings" }} />
          <Stack.Screen name="admin" options={{ headerShown: true, title: "Admin Dashboard" }} />
        </Stack>
      </AuthGate>
    </AuthProvider>
  );
}
