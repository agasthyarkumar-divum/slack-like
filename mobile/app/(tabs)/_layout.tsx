import { Tabs } from "expo-router";
import { Bell, Home, Search, User } from "lucide-react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts } from "@/lib/theme/tokens";

export default function TabsLayout() {
  const { colors } = useTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accentMoss,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: {
          backgroundColor: colors.bgSurfaceRaised,
          borderTopColor: colors.borderHairline,
          borderTopWidth: 1,
        },
        tabBarLabelStyle: { fontFamily: fonts.bodyMedium, fontSize: 11 },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: "Home", tabBarIcon: ({ color }) => <Home size={22} color={color} strokeWidth={1.5} /> }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: "Search",
          tabBarIcon: ({ color }) => <Search size={22} color={color} strokeWidth={1.5} />,
        }}
      />
      <Tabs.Screen
        name="notifications"
        options={{
          title: "Notifications",
          tabBarIcon: ({ color }) => <Bell size={22} color={color} strokeWidth={1.5} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: "Profile", tabBarIcon: ({ color }) => <User size={22} color={color} strokeWidth={1.5} /> }}
      />
    </Tabs>
  );
}
