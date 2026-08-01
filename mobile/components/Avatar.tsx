import { Image, StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii } from "@/lib/theme/tokens";

type AvatarProps = {
  name: string;
  imageUri?: string | null;
  size?: number;
};

function initialsFor(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

// Soft rounded squares, not circles — a small deliberate departure from the
// typical circular-avatar chat convention (see design brief).
export function Avatar({ name, imageUri, size = 40 }: AvatarProps) {
  const { colors } = useTheme();
  const style = {
    width: size,
    height: size,
    borderRadius: Math.max(radii.sm, size * 0.28),
  };

  if (imageUri) {
    return <Image source={{ uri: imageUri }} style={[styles.image, style]} />;
  }

  return (
    <View style={[styles.fallback, style, { backgroundColor: colors.accentMossSoft }]}>
      <Text
        style={[
          styles.initials,
          { color: colors.accentMoss, fontSize: size * 0.4 },
        ]}
      >
        {initialsFor(name)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  image: {
    resizeMode: "cover",
  },
  fallback: {
    alignItems: "center",
    justifyContent: "center",
  },
  initials: {
    fontFamily: fonts.bodySemiBold,
  },
});
