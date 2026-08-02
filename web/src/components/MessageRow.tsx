import { useState } from "react";
import { SmilePlus } from "lucide-react";

import { Avatar } from "@/components/Avatar";
import { EmojiPicker } from "@/components/EmojiPicker";
import { ReactionPills } from "@/components/ReactionPills";
import type { Message } from "@/lib/api/types";
import styles from "./MessageRow.module.css";

function timeLabel(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

type MessageRowProps = {
  message: Message;
  authorName: string;
  onToggleReaction: (emoji: string) => void;
  onOpenThread?: () => void;
};

export function MessageRow({ message, authorName, onToggleReaction, onOpenThread }: MessageRowProps) {
  const [pickerOpen, setPickerOpen] = useState(false);

  return (
    <div className={styles.row}>
      <Avatar name={authorName} size={36} />
      <div className={styles.content}>
        <div className={styles.meta}>
          <span className={styles.author}>{authorName}</span>
          <span className={styles.time}>{timeLabel(message.created_at)}</span>
          {message.is_edited ? <span className={styles.edited}>(edited)</span> : null}
        </div>
        {message.content ? <div className={styles.body}>{message.content}</div> : null}
        <ReactionPills reactions={message.reactions} onToggle={onToggleReaction} />
        {onOpenThread && message.reply_count > 0 ? (
          <button type="button" className={styles.threadLink} onClick={onOpenThread}>
            {message.reply_count} {message.reply_count === 1 ? "reply" : "replies"}
          </button>
        ) : onOpenThread ? (
          <button type="button" className={styles.replyLink} onClick={onOpenThread}>
            Reply in thread
          </button>
        ) : null}
      </div>
      <div className={styles.hoverActions}>
        <button
          type="button"
          className={styles.reactButton}
          aria-label="Add reaction"
          onClick={() => setPickerOpen((v) => !v)}
        >
          <SmilePlus size={16} strokeWidth={1.5} />
        </button>
        {pickerOpen ? (
          <div className={styles.pickerAnchor}>
            <EmojiPicker
              onSelect={(emoji) => onToggleReaction(emoji)}
              onClose={() => setPickerOpen(false)}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
