import { useEffect, useRef, useState } from "react";
import { Menu, Moon, Search, Settings, Sun } from "lucide-react";

import { Composer } from "@/components/Composer";
import { MessageRow } from "@/components/MessageRow";
import { listMessages, sendMessage, toggleReaction } from "@/lib/api/messages";
import { listMembers } from "@/lib/api/channels";
import { useUserName } from "@/lib/api/userDirectory";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { useWS } from "@/lib/ws/WSContext";
import type { Channel, Message } from "@/lib/api/types";
import styles from "./ConversationPane.module.css";

type ConversationPaneProps = {
  channel: Channel;
  presence: Record<string, string>;
  onOpenThread: (message: Message) => void;
  onOpenSearch: () => void;
  onOpenSettings: () => void;
  onToggleDrawer?: () => void;
};

export function ConversationPane({
  channel,
  presence,
  onOpenThread,
  onOpenSearch,
  onOpenSettings,
  onToggleDrawer,
}: ConversationPaneProps) {
  const { user } = useAuth();
  const { isDark, toggle } = useTheme();
  const { subscribe, send } = useWS();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dmOtherUserId, setDmOtherUserId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const dmOtherName = useUserName(channel.type === "dm" ? dmOtherUserId : null);

  useEffect(() => {
    setIsLoading(true);
    setMessages([]);
    setDmOtherUserId(null);
    let cancelled = false;

    listMessages(channel.id).then((page) => {
      if (cancelled) return;
      setMessages(page.items.slice().reverse()); // oldest first for top-to-bottom rendering
      setIsLoading(false);
    });

    if (channel.type === "dm") {
      listMembers(channel.id).then((members) => {
        if (cancelled) return;
        const other = members.find((m) => m.user_id !== user?.id);
        if (other) setDmOtherUserId(other.user_id);
      });
    }

    return () => {
      cancelled = true;
    };
  }, [channel.id, channel.type, user?.id]);

  useEffect(() => {
    const unsubNew = subscribe("message.new", (data) => {
      if (data.channel_id !== channel.id) return;
      const message = data as unknown as Message;
      setMessages((prev) => (prev.some((m) => m.id === message.id) ? prev : [...prev, message]));
    });
    const unsubEdited = subscribe("message.edited", (data) => {
      if (data.channel_id !== channel.id) return;
      setMessages((prev) =>
        prev.map((m) => (m.id === data.id ? { ...m, content: data.content as string, is_edited: true } : m))
      );
    });
    const unsubDeleted = subscribe("message.deleted", (data) => {
      if (data.channel_id !== channel.id) return;
      setMessages((prev) => prev.filter((m) => m.id !== data.id));
    });
    const unsubThreadReply = subscribe("thread.reply.new", (data) => {
      if (data.channel_id !== channel.id) return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === data.parent_id ? { ...m, reply_count: m.reply_count + 1, last_reply_at: data.created_at as string } : m
        )
      );
    });
    const unsubReaction = subscribe("message.reaction", (data) => {
      if (data.channel_id !== channel.id) return;
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== data.id) return m;
          const totals = data.reactions as { emoji: string; count: number }[];
          const changedEmoji = data.emoji as string;
          const changedByMe = data.user_id === user?.id;
          return {
            ...m,
            reactions: totals.map((t) => ({
              emoji: t.emoji,
              count: t.count,
              me: t.emoji === changedEmoji && changedByMe ? (data.added as boolean) : m.reactions.find((r) => r.emoji === t.emoji)?.me ?? false,
            })),
          };
        })
      );
    });

    return () => {
      unsubNew();
      unsubEdited();
      unsubDeleted();
      unsubThreadReply();
      unsubReaction();
    };
  }, [channel.id, subscribe, user?.id]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages.length]);

  // Marks the newest message read whenever it changes, as long as it's not
  // ours — the source of truth for unread counts is server-side (MessageRead
  // rows), so switching channels needs this, not just clearing the sidebar
  // badge locally, or a reload would bring the badge right back.
  const newestMessageId = messages[messages.length - 1]?.id;
  useEffect(() => {
    if (!newestMessageId) return;
    const newest = messages[messages.length - 1];
    if (newest && newest.sender_id && newest.sender_id !== user?.id) {
      send("read_receipt.update", { message_id: newest.id });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newestMessageId, user?.id]);

  async function handleSend(content: string) {
    const message = await sendMessage(channel.id, { content });
    setMessages((prev) => (prev.some((m) => m.id === message.id) ? prev : [...prev, message]));
  }

  async function handleToggleReaction(messageId: string, emoji: string) {
    const updated = await toggleReaction(messageId, emoji);
    setMessages((prev) => prev.map((m) => (m.id === messageId ? updated : m)));
  }

  const isDm = channel.type === "dm";
  const title = isDm ? dmOtherName || "Direct message" : `#${channel.name}`;
  const subtitle = isDm
    ? (dmOtherUserId && presence[dmOtherUserId]) === "online"
      ? "Online"
      : "Offline"
    : channel.topic || "No topic set.";

  return (
    <div className={styles.pane}>
      <header className={styles.header}>
        {onToggleDrawer ? (
          <button type="button" className={styles.iconButton} aria-label="Open channels" onClick={onToggleDrawer}>
            <Menu size={18} strokeWidth={1.5} />
          </button>
        ) : null}
        <div className={styles.headerText}>
          <span className={styles.headerTitle}>{title}</span>
          <span className={styles.headerSubtitle}>{subtitle}</span>
        </div>
        <div className={styles.headerActions}>
          <button type="button" className={styles.iconButton} aria-label="Toggle theme" onClick={toggle}>
            {isDark ? <Sun size={18} strokeWidth={1.5} /> : <Moon size={18} strokeWidth={1.5} />}
          </button>
          <button type="button" className={styles.iconButton} aria-label="Search" onClick={onOpenSearch}>
            <Search size={18} strokeWidth={1.5} />
          </button>
          <button type="button" className={styles.iconButton} aria-label="Settings" onClick={onOpenSettings}>
            <Settings size={18} strokeWidth={1.5} />
          </button>
        </div>
      </header>

      <div className={styles.list} ref={listRef}>
        {isLoading ? (
          <div className={styles.empty}>Loading…</div>
        ) : messages.length === 0 ? (
          <div className={styles.empty}>
            <span className={styles.emptyTitle}>No messages yet.</span>
            <span className={styles.emptySubtitle}>Say something.</span>
          </div>
        ) : (
          messages.map((m) => (
            <ConnectedMessageRow
              key={m.id}
              message={m}
              onToggleReaction={(emoji) => handleToggleReaction(m.id, emoji)}
              onOpenThread={() => onOpenThread(m)}
            />
          ))
        )}
      </div>

      <Composer onSend={handleSend} />
    </div>
  );
}

function ConnectedMessageRow({
  message,
  onToggleReaction,
  onOpenThread,
}: {
  message: Message;
  onToggleReaction: (emoji: string) => void;
  onOpenThread: () => void;
}) {
  const authorName = useUserName(message.sender_id);
  return (
    <MessageRow
      message={message}
      authorName={authorName || "Someone"}
      onToggleReaction={onToggleReaction}
      onOpenThread={onOpenThread}
    />
  );
}
