import { Pressable, StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
import { radii, spacing } from "@/lib/theme/tokens";

// A fixed curated set rather than a full emoji-keyboard integration — plenty
// for an internal team chat's reactions, and avoids a heavy dependency.
export const CURATED_EMOJI = ["👍", "❤️", "😂", "🎉", "👀", "🙏", "🔥", "✅"];

type EmojiPickerProps = {
  onSelect: (emoji: string) => void;
};

// Rendered inline (not as a floating overlay) — simplest reliable layout on
// RN without a portal/positioning library, and reads fine as a small row
// that expands directly under the message it's reacting to.
export function EmojiPicker({ onSelect }: EmojiPickerProps) {
  const { colors } = useTheme();
  return (
    <View style={[styles.row, { borderColor: colors.borderHairline, backgroundColor: colors.bgSurfaceRaised }]}>
      {CURATED_EMOJI.map((emoji) => (
        <Pressable key={emoji} onPress={() => onSelect(emoji)} style={styles.emoji}>
          <Text style={styles.emojiText}>{emoji}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignSelf: "flex-start",
    borderWidth: 1,
    borderRadius: radii.md,
    padding: 4,
    marginTop: 4,
    gap: 2,
  },
  emoji: {
    width: 30,
    height: 30,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.sm,
  },
  emojiText: { fontSize: 17 },
});
