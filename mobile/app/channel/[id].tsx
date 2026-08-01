import { useLocalSearchParams, useNavigation } from "expo-router";
import { Send } from "lucide-react-native";
import { useCallback, useEffect, useRef, useState } from "react";
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
import { getChannel } from "@/lib/api/channels";
import { listMessages, sendMessage } from "@/lib/api/messages";
import type { Channel, Message } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";
import { useWS } from "@/lib/ws/WSContext";

const TYPING_TIMEOUT_MS = 4000;
const TYPING_DEBOUNCE_MS = 1500;

function timeLabel(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function ChatScreen() {
  const { id: channelId } = useLocalSearchParams<{ id: string }>();
  const navigation = useNavigation();
  const { user } = useAuth();
  const { colors } = useTheme();
  const { subscribe, send } = useWS();

  const [channel, setChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<Message[]>([]); // newest first (index 0)
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [typingUserIds, setTypingUserIds] = useState<Set<string>>(new Set());

  const typingTimeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const lastTypingSentAtRef = useRef(0);

  useEffect(() => {
    if (!channelId) return;
    (async () => {
      const [channelData, messagesData] = await Promise.all([
        getChannel(channelId),
        listMessages(channelId),
      ]);
      setChannel(channelData);
      navigation.setOptions({ title: channelData.type === "dm" ? channelData.name : `#${channelData.name}` });
      setMessages(messagesData.items);
      setNextCursor(messagesData.next_cursor);
      setIsLoading(false);
    })();
  }, [channelId, navigation]);

  useEffect(() => {
    if (!channelId) return undefined;

    const unsubNew = subscribe("message.new", (data) => {
      if (data.channel_id !== channelId) return;
      setMessages((prev) => (prev.some((m) => m.id === data.id) ? prev : [data as unknown as Message, ...prev]));
    });
    const unsubEdited = subscribe("message.edited", (data) => {
      if (data.channel_id !== channelId) return;
      setMessages((prev) =>
        prev.map((m) => (m.id === data.id ? { ...m, content: data.content as string, is_edited: true } : m))
      );
    });
    const unsubDeleted = subscribe("message.deleted", (data) => {
      if (data.channel_id !== channelId) return;
      setMessages((prev) => prev.filter((m) => m.id !== data.id));
    });
    const unsubTypingStart = subscribe("typing.start", (data) => {
      if (data.channel_id !== channelId || data.user_id === user?.id) return;
      const uid = data.user_id as string;
      setTypingUserIds((prev) => new Set(prev).add(uid));
      const existing = typingTimeoutsRef.current.get(uid);
      if (existing) clearTimeout(existing);
      typingTimeoutsRef.current.set(
        uid,
        setTimeout(() => {
          setTypingUserIds((prev) => {
            const next = new Set(prev);
            next.delete(uid);
            return next;
          });
        }, TYPING_TIMEOUT_MS)
      );
    });
    const unsubTypingStop = subscribe("typing.stop", (data) => {
      if (data.channel_id !== channelId) return;
      const uid = data.user_id as string;
      setTypingUserIds((prev) => {
        const next = new Set(prev);
        next.delete(uid);
        return next;
      });
    });

    return () => {
      unsubNew();
      unsubEdited();
      unsubDeleted();
      unsubTypingStart();
      unsubTypingStop();
    };
  }, [channelId, subscribe, user?.id]);

  const handleLoadMore = useCallback(async () => {
    if (!channelId || !nextCursor || isLoadingMore) return;
    setIsLoadingMore(true);
    try {
      const page = await listMessages(channelId, nextCursor);
      setMessages((prev) => [...prev, ...page.items]);
      setNextCursor(page.next_cursor);
    } finally {
      setIsLoadingMore(false);
    }
  }, [channelId, nextCursor, isLoadingMore]);

  function handleDraftChange(text: string) {
    setDraft(text);
    if (!channelId) return;
    const now = Date.now();
    if (now - lastTypingSentAtRef.current > TYPING_DEBOUNCE_MS) {
      send("typing.start", { channel_id: channelId });
      lastTypingSentAtRef.current = now;
    }
  }

  async function handleSend() {
    const content = draft.trim();
    if (!content || !channelId || isSending) return;
    setIsSending(true);
    setDraft("");
    try {
      const message = await sendMessage(channelId, { content });
      setMessages((prev) => (prev.some((m) => m.id === message.id) ? prev : [message, ...prev]));
      send("typing.stop", { channel_id: channelId });
    } finally {
      setIsSending(false);
    }
  }

  if (isLoading || !channel) {
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
      <FlatList
        style={styles.flex}
        data={messages}
        inverted
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.4}
        ListFooterComponent={isLoadingMore ? <ActivityIndicator style={styles.loadingMore} color={colors.accentMoss} /> : null}
        renderItem={({ item }) => (
          <MessageBubble
            content={item.content}
            isMine={item.sender_id === user?.id}
            isEdited={item.is_edited ?? false}
            timeLabel={timeLabel(item.created_at)}
            hasAttachment={item.attachment_ids.length > 0}
          />
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>No messages yet.</Text>
            <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>Say something.</Text>
          </View>
        }
      />

      {typingUserIds.size > 0 ? (
        <Text style={[styles.typingIndicator, { color: colors.textSecondary }]}>
          {typingUserIds.size === 1 ? "Someone is typing…" : "Several people are typing…"}
        </Text>
      ) : null}

      <View style={[styles.composer, { borderTopColor: colors.borderHairline, backgroundColor: colors.bgSurfaceRaised }]}>
        <TextInput
          value={draft}
          onChangeText={handleDraftChange}
          placeholder="Message…"
          placeholderTextColor={colors.textSecondary}
          style={[styles.composerInput, { backgroundColor: colors.bgSurface, color: colors.textPrimary }]}
          multiline
        />
        <Pressable
          onPress={handleSend}
          disabled={!draft.trim() || isSending}
          accessibilityRole="button"
          accessibilityLabel="Send message"
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
  listContent: { paddingVertical: spacing.md },
  loadingMore: { marginVertical: spacing.md },
  emptyContainer: {
    // inverted list — this renders visually at the top of the screen, but flex
    // centering still reads naturally for an empty conversation.
    transform: [{ scaleY: -1 }],
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.xxl * 2,
    gap: spacing.xs,
  },
  emptyTitle: { fontFamily: fonts.display, fontSize: 18 },
  emptySubtitle: { fontFamily: fonts.body, fontSize: 14 },
  typingIndicator: {
    fontFamily: fonts.body,
    fontSize: 12,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xs,
  },
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
