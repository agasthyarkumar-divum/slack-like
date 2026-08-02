import { Check, CheckCheck } from "lucide-react-native";
import { ImageBackground, StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";
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

  if (isMine) {
    return (
      <View style={[styles.row, styles.rowMine]}>
        <View style={bubbleStyle}>{body}</View>
      </View>
    );
  }

  return (
    <View style={[styles.row, styles.rowTheirs]}>
      <ImageBackground
        source={require("@/assets/paper-grain.png")}
        resizeMode="repeat"
        imageStyle={{ opacity: isDark ? 0.5 : 0.3 }}
        style={bubbleStyle}
      >
        {body}
      </ImageBackground>
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
});
