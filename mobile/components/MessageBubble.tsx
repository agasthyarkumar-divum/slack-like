import { Check, CheckCheck, SmilePlus } from "lucide-react-native";
import { ImageBackground, Pressable, StyleSheet, Text, View } from "react-native";

import { EmojiPicker } from "@/components/EmojiPicker";
import { useTheme } from "@/lib/theme/ThemeContext";
import type { ReactionSummary } from "@/lib/api/types";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

type DeliveryStatus = "sent" | "delivered" | "seen";

type MessageBubbleProps = {
  content: string | null;
  isMine: boolean;
  isEdited?: boolean;
  timeLabel: string;
  hasAttachment?: boolean;
  senderName?: string;
  /** Only pass this for the sender's own latest message — a check per
   * message would be noisy; one running status at the bottom of the
   * conversation is the usual chat-app convention. */
  deliveryStatus?: DeliveryStatus;
  reactions?: ReactionSummary[];
  onToggleReaction?: (emoji: string) => void;
  isPickerOpen?: boolean;
  onTogglePicker?: () => void;
  replyCount?: number;
  onOpenThread?: () => void;
};

// Signature element: a barely-visible warm paper-grain noise overlay on
// received bubbles (bg.surface) — felt more than seen, so the chat surface
// reads as tactile rather than flat digital. Sent bubbles (moss, already a
// saturated fill) skip it to avoid muddying the accent color.
export function MessageBubble({
  content,
  isMine,
  isEdited,
  timeLabel,
  hasAttachment,
  senderName,
  deliveryStatus,
  reactions = [],
  onToggleReaction,
  isPickerOpen,
  onTogglePicker,
  replyCount = 0,
  onOpenThread,
}: MessageBubbleProps) {
  const { colors, isDark } = useTheme();

  const bubbleStyle = [
    styles.bubble,
    isMine
      ? { backgroundColor: colors.accentMoss, borderBottomRightRadius: radii.sm }
      : { backgroundColor: colors.bgSurface, borderBottomLeftRadius: radii.sm },
  ];

  const textColor = isMine ? "#FFFFFF" : colors.textPrimary;
  const metaColor = isMine ? "rgba(255,255,255,0.75)" : colors.textSecondary;

  const body = (
    <>
      {senderName ? <Text style={[styles.senderName, { color: colors.accentMoss }]}>{senderName}</Text> : null}
      {hasAttachment ? (
        <View style={[styles.attachmentChip, { borderColor: metaColor }]}>
          <Text style={[styles.attachmentText, { color: textColor }]}>📎 attachment</Text>
        </View>
      ) : null}
      {content ? <Text style={[styles.content, { color: textColor }]}>{content}</Text> : null}
      <View style={styles.metaRow}>
        <Text style={[styles.meta, { color: metaColor }]}>
          {timeLabel}
          {isEdited ? " · edited" : ""}
        </Text>
        {deliveryStatus === "seen" ? (
          <CheckCheck size={13} color={isMine ? "#FFFFFF" : colors.accentMoss} strokeWidth={2} />
        ) : deliveryStatus === "delivered" ? (
          <CheckCheck size={13} color={metaColor} strokeWidth={2} />
        ) : deliveryStatus === "sent" ? (
          <Check size={13} color={metaColor} strokeWidth={2} />
        ) : null}
      </View>
    </>
  );

  const bubble = isMine ? (
    <View style={bubbleStyle}>{body}</View>
  ) : (
    <ImageBackground
      source={require("@/assets/paper-grain.png")}
      resizeMode="repeat"
      imageStyle={{ opacity: isDark ? 0.5 : 0.3 }}
      style={bubbleStyle}
    >
      {body}
    </ImageBackground>
  );

  return (
    <View style={[styles.row, isMine ? styles.rowMine : styles.rowTheirs]}>
      <View style={isMine ? styles.stackMine : styles.stackTheirs}>
        <View style={styles.bubbleRow}>
          {bubble}
          {onToggleReaction ? (
            <Pressable
              onPress={onTogglePicker}
              accessibilityRole="button"
              accessibilityLabel="Add reaction"
              style={[styles.reactTrigger, { borderColor: colors.borderHairline, backgroundColor: colors.bgSurfaceRaised }]}
            >
              <SmilePlus size={13} color={colors.textSecondary} strokeWidth={1.5} />
            </Pressable>
          ) : null}
        </View>

        {isPickerOpen && onToggleReaction ? (
          <EmojiPicker onSelect={onToggleReaction} />
        ) : null}

        {reactions.length > 0 ? (
          <View style={[styles.reactionRow, isMine && styles.reactionRowMine]}>
            {reactions.map((r) => (
              <Pressable
                key={r.emoji}
                onPress={() => onToggleReaction?.(r.emoji)}
                style={[
                  styles.reactionPill,
                  { borderColor: colors.borderHairline, backgroundColor: colors.bgSurface },
                  r.me && { borderColor: colors.accentMoss, backgroundColor: colors.accentMossSoft },
                ]}
              >
                <Text style={styles.reactionEmoji}>{r.emoji}</Text>
                <Text style={[styles.reactionCount, { color: r.me ? colors.accentMoss : colors.textSecondary }]}>
                  {r.count}
                </Text>
              </Pressable>
            ))}
          </View>
        ) : null}

        {onOpenThread ? (
          <Pressable onPress={onOpenThread} style={[styles.threadLink, isMine && styles.threadLinkMine]}>
            <Text style={[styles.threadLinkText, { color: replyCount > 0 ? colors.accentMoss : colors.textSecondary }]}>
              {replyCount > 0 ? `${replyCount} ${replyCount === 1 ? "reply" : "replies"}` : "Reply in thread"}
            </Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", paddingHorizontal: spacing.lg, marginVertical: spacing.xs },
  rowMine: { justifyContent: "flex-end" },
  rowTheirs: { justifyContent: "flex-start" },
  bubble: {
    maxWidth: "78%",
    borderRadius: radii.lg,
    paddingVertical: spacing.sm + 2,
    paddingHorizontal: spacing.md + 2,
    gap: 2,
    overflow: "hidden",
  },
  senderName: { fontFamily: fonts.bodySemiBold, fontSize: 12, marginBottom: 1 },
  content: { fontFamily: fonts.body, fontSize: 15, lineHeight: 21 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 2 },
  meta: { fontFamily: fonts.body, fontSize: 11 },
  attachmentChip: {
    borderWidth: 1,
    borderRadius: radii.sm,
    paddingVertical: 4,
    paddingHorizontal: 8,
    alignSelf: "flex-start",
    marginBottom: 4,
  },
  attachmentText: { fontFamily: fonts.bodyMedium, fontSize: 12 },
  stackMine: { alignItems: "flex-end", maxWidth: "82%" },
  stackTheirs: { alignItems: "flex-start", maxWidth: "82%" },
  bubbleRow: { flexDirection: "row", alignItems: "flex-end", gap: spacing.xs },
  reactTrigger: {
    width: 26,
    height: 26,
    borderRadius: radii.sm,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  reactionRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.xs, marginTop: 4 },
  reactionRowMine: { justifyContent: "flex-end" },
  reactionPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    borderWidth: 1,
    borderRadius: radii.pill,
    paddingVertical: 2,
    paddingHorizontal: spacing.sm,
  },
  reactionEmoji: { fontSize: 13 },
  reactionCount: { fontFamily: fonts.bodyMedium, fontSize: 12 },
  threadLink: { marginTop: 4 },
  threadLinkMine: { alignSelf: "flex-end" },
  threadLinkText: { fontFamily: fonts.bodyMedium, fontSize: 12 },
});
