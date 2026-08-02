import { useState } from "react";
import type { KeyboardEvent } from "react";
import { Send } from "lucide-react";

import styles from "./Composer.module.css";

type ComposerProps = {
  placeholder?: string;
  onSend: (content: string) => void | Promise<void>;
  onChange?: (value: string) => void;
};

export function Composer({ placeholder = "Message…", onSend, onChange }: ComposerProps) {
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);

  async function handleSend() {
    const content = draft.trim();
    if (!content || isSending) return;
    setIsSending(true);
    setDraft("");
    try {
      await onSend(content);
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className={styles.composer}>
      <textarea
        className={styles.input}
        value={draft}
        placeholder={placeholder}
        rows={1}
        onChange={(e) => {
          setDraft(e.target.value);
          onChange?.(e.target.value);
        }}
        onKeyDown={handleKeyDown}
      />
      <button
        type="button"
        className={styles.send}
        disabled={!draft.trim() || isSending}
        onClick={handleSend}
        aria-label="Send message"
      >
        <Send size={18} strokeWidth={1.5} />
      </button>
    </div>
  );
}
