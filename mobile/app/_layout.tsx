import {
  Fraunces_400Regular,
  Fraunces_600SemiBold,
} from "@expo-google-fonts/fraunces";
import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  useFonts,
} from "@expo-google-fonts/inter";
import { Redirect, Stack, usePathname } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import type { PropsWithChildren } from "react";

import { AuthProvider, useAuth } from "@/lib/auth/AuthContext";
import { ThemeProvider, useTheme } from "@/lib/theme/ThemeContext";
import { fonts } from "@/lib/theme/tokens";
import { WSProvider } from "@/lib/ws/WSContext";

SplashScreen.preventAutoHideAsync().catch(() => {});

function AuthGate({ children }: PropsWithChildren) {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();

  if (isLoading) return null;

  const isOnLoginScreen = pathname === "/login";
  if (!user && !isOnLoginScreen) return <Redirect href="/login" />;
  if (user && isOnLoginScreen) return <Redirect href="/" />;

  return <>{children}</>;
}

function ThemedStack() {
  const { colors } = useTheme();
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        headerStyle: { backgroundColor: colors.bgSurfaceRaised },
        headerTintColor: colors.textPrimary,
        headerTitleStyle: { fontFamily: fonts.display },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: colors.bgBase },
      }}
    >
      <Stack.Screen name="login" />
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="channel/[id]" options={{ headerShown: true, title: "" }} />
      <Stack.Screen name="settings" options={{ headerShown: true, title: "Settings" }} />
      <Stack.Screen name="admin" options={{ headerShown: true, title: "Admin Dashboard" }} />
    </Stack>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Fraunces_400Regular,
    Fraunces_600SemiBold,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
  });

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync().catch(() => {});
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <ThemeProvider>
      <AuthProvider>
        <WSProvider>
          <AuthGate>
            <ThemedStack />
          </AuthGate>
        </WSProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
