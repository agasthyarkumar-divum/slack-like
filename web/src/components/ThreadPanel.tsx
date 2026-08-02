import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";

import { Composer } from "@/components/Composer";
import { MessageRow } from "@/components/MessageRow";
import { useUserName } from "@/lib/api/userDirectory";
import { listReplies, sendMessage, toggleReaction } from "@/lib/api/messages";
import { useWS } from "@/lib/ws/WSContext";
import type { Message } from "@/lib/api/types";
import styles from "./ThreadPanel.module.css";

type ThreadPanelProps = {
  message: Message;
  onClose: () => void;
  onParentUpdate: (message: Message) => void;
};

export function ThreadPanel({ message, onClose, onParentUpdate }: ThreadPanelProps) {
  const { subscribe } = useWS();
  const [parent, setParent] = useState(message);
  const [replies, setReplies] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);
  const parentAuthorName = useUserName(parent.sender_id);

  useEffect(() => {
    setIsLoading(true);
    listReplies(message.id).then((res) => {
      setParent(res.parent);
      setReplies(res.items);
      setIsLoading(false);
    });
  }, [message.id]);

  useEffect(() => {
    const unsub = subscribe("thread.reply.new", (data) => {
      if (data.parent_id !== message.id) return;
      const reply = data as unknown as Message;
      setReplies((prev) => (prev.some((r) => r.id === reply.id) ? prev : [...prev, reply]));
      setParent((prev) => {
        const updated = { ...prev, reply_count: prev.reply_count + 1, last_reply_at: reply.created_at };
        onParentUpdate(updated);
        return updated;
      });
    });
    return unsub;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message.id, subscribe]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [replies.length]);

  async function handleSend(content: string) {
    const reply = await sendMessage(parent.channel_id!, { content, reply_to_id: parent.id });
    setReplies((prev) => (prev.some((r) => r.id === reply.id) ? prev : [...prev, reply]));
    setParent((prev) => {
      const updated = { ...prev, reply_count: prev.reply_count + 1 };
      onParentUpdate(updated);
      return updated;
    });
  }

  async function handleToggleReaction(messageId: string, emoji: string) {
    const updated = await toggleReaction(messageId, emoji);
    if (messageId === parent.id) {
      setParent(updated);
      onParentUpdate(updated);
    } else {
      setReplies((prev) => prev.map((r) => (r.id === messageId ? updated : r)));
    }
  }

  return (
    <aside className={styles.panel}>
      <header className={styles.header}>
        <span className={styles.title}>Thread</span>
        <button type="button" className={styles.close} aria-label="Close thread" onClick={onClose}>
          <X size={18} strokeWidth={1.5} />
        </button>
      </header>

      <div className={styles.parentWrap}>
        <MessageRow
          message={parent}
          authorName={parentAuthorName || "Someone"}
          onToggleReaction={(emoji) => handleToggleReaction(parent.id, emoji)}
        />
      </div>

      <div className={styles.repliesList} ref={listRef}>
        {isLoading ? (
          <div className={styles.loading}>Loading…</div>
        ) : replies.length === 0 ? (
          <div className={styles.loading}>No replies yet.</div>
        ) : (
          replies.map((r) => (
            <ConnectedReply key={r.id} message={r} onToggleReaction={(emoji) => handleToggleReaction(r.id, emoji)} />
          ))
        )}
      </div>

      <Composer placeholder="Reply…" onSend={handleSend} />
    </aside>
  );
}

function ConnectedReply({
  message,
  onToggleReaction,
}: {
  message: Message;
  onToggleReaction: (emoji: string) => void;
}) {
  const authorName = useUserName(message.sender_id);
  return <MessageRow message={message} authorName={authorName || "Someone"} onToggleReaction={onToggleReaction} />;
}
