import { useLocalSearchParams, useNavigation } from "expo-router";
import { Send } from "lucide-react-native";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { MessageBubble } from "@/components/MessageBubble";
import { listReplies, sendMessage, toggleReaction } from "@/lib/api/messages";
import type { Message } from "@/lib/api/types";
import { useUserName } from "@/lib/api/userDirectory";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";
import { useWS } from "@/lib/ws/WSContext";

function timeLabel(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function ReplyRow({
  item,
  isMine,
  pickerOpenFor,
  onTogglePicker,
  onToggleReaction,
}: {
  item: Message;
  isMine: boolean;
  pickerOpenFor: string | null;
  onTogglePicker: (id: string) => void;
  onToggleReaction: (id: string, emoji: string) => void;
}) {
  const senderName = useUserName(isMine ? null : item.sender_id);
  return (
    <MessageBubble
      content={item.content}
      isMine={isMine}
      isEdited={item.is_edited ?? false}
      timeLabel={timeLabel(item.created_at)}
      hasAttachment={item.attachment_ids.length > 0}
      senderName={isMine ? undefined : senderName}
      reactions={item.reactions}
      onToggleReaction={(emoji) => onToggleReaction(item.id, emoji)}
      isPickerOpen={pickerOpenFor === item.id}
      onTogglePicker={() => onTogglePicker(item.id)}
    />
  );
}

export default function ThreadScreen() {
  const { messageId } = useLocalSearchParams<{ id: string; messageId: string }>();
  const navigation = useNavigation();
  const { user } = useAuth();
  const { colors } = useTheme();
  const { subscribe } = useWS();

  const [parent, setParent] = useState<Message | null>(null);
  const [replies, setReplies] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [pickerOpenFor, setPickerOpenFor] = useState<string | null>(null);

  const parentAuthorName = useUserName(parent?.sender_id ?? null);

  useEffect(() => {
    if (!messageId) return;
    (async () => {
      const res = await listReplies(messageId);
      setParent(res.parent);
      setReplies(res.items);
      setIsLoading(false);
    })();
  }, [messageId]);

  useEffect(() => {
    navigation.setOptions({ title: "Thread" });
  }, [navigation]);

  useEffect(() => {
    if (!messageId) return undefined;
    const unsub = subscribe("thread.reply.new", (data) => {
      if (data.parent_id !== messageId) return;
      const reply = data as unknown as Message;
      setReplies((prev) => (prev.some((r) => r.id === reply.id) ? prev : [...prev, reply]));
      setParent((prev) => (prev ? { ...prev, reply_count: prev.reply_count + 1 } : prev));
    });
    return unsub;
  }, [messageId, subscribe]);

  async function handleSend() {
    const content = draft.trim();
    if (!content || !parent?.channel_id || isSending) return;
    setIsSending(true);
    setDraft("");
    try {
      const reply = await sendMessage(parent.channel_id, { content, reply_to_id: parent.id });
      setReplies((prev) => (prev.some((r) => r.id === reply.id) ? prev : [...prev, reply]));
      setParent((prevParent) => (prevParent ? { ...prevParent, reply_count: prevParent.reply_count + 1 } : prevParent));
    } finally {
      setIsSending(false);
    }
  }

  async function handleToggleReaction(id: string, emoji: string) {
    setPickerOpenFor(null);
    const updated = await toggleReaction(id, emoji);
    if (parent && id === parent.id) setParent(updated);
    else setReplies((prev) => prev.map((r) => (r.id === id ? updated : r)));
  }

  if (isLoading || !parent) {
    return (
      <View style={[styles.center, { backgroundColor: colors.bgBase }]}>
        <ActivityIndicator color={colors.accentMoss} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: colors.bgBase }]}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
      <View style={[styles.parentWrap, { borderBottomColor: colors.borderHairline }]}>
        <MessageBubble
          content={parent.content}
          isMine={parent.sender_id === user?.id}
          isEdited={parent.is_edited ?? false}
          timeLabel={timeLabel(parent.created_at)}
          hasAttachment={parent.attachment_ids.length > 0}
          senderName={parent.sender_id === user?.id ? undefined : parentAuthorName}
          reactions={parent.reactions}
          onToggleReaction={(emoji) => handleToggleReaction(parent.id, emoji)}
          isPickerOpen={pickerOpenFor === parent.id}
          onTogglePicker={() => setPickerOpenFor((prev) => (prev === parent.id ? null : parent.id))}
        />
      </View>

      <FlatList
        style={styles.flex}
        data={replies}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => (
          <ReplyRow
            item={item}
            isMine={item.sender_id === user?.id}
            pickerOpenFor={pickerOpenFor}
            onTogglePicker={(id) => setPickerOpenFor((prev) => (prev === id ? null : id))}
            onToggleReaction={handleToggleReaction}
          />
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>No replies yet.</Text>
          </View>
        }
      />

      <View style={[styles.composer, { borderTopColor: colors.borderHairline, backgroundColor: colors.bgSurfaceRaised }]}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          placeholder="Reply…"
          placeholderTextColor={colors.textSecondary}
          style={[styles.composerInput, { backgroundColor: colors.bgSurface, color: colors.textPrimary }]}
          multiline
        />
        <Pressable
          onPress={handleSend}
          disabled={!draft.trim() || isSending}
          accessibilityRole="button"
          accessibilityLabel="Send reply"
          style={[styles.sendButton, { backgroundColor: colors.accentMoss, opacity: draft.trim() ? 1 : 0.5 }]}
        >
          {isSending ? <ActivityIndicator size="small" color="#FFF" /> : <Send size={18} color="#FFF" strokeWidth={1.5} />}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  parentWrap: { borderBottomWidth: 1, paddingVertical: spacing.sm },
  listContent: { paddingVertical: spacing.md },
  emptyContainer: { alignItems: "center", justifyContent: "center", paddingVertical: spacing.xxl, gap: spacing.xs },
  emptyTitle: { fontFamily: fonts.body, fontSize: 14 },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
    padding: spacing.md,
    borderTopWidth: 1,
  },
  composerInput: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: 15,
    borderRadius: radii.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
    maxHeight: 120,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
  },
});
