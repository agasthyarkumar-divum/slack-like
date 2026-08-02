import { useEffect, useRef, useState } from "react";

import { Avatar } from "@/components/Avatar";
import { Modal } from "@/components/Modal";
import { search as runSearch } from "@/lib/api/search";
import { useUserName } from "@/lib/api/userDirectory";
import type { Channel, Message, SearchResponse, SearchType } from "@/lib/api/types";
import styles from "./SearchModal.module.css";

const TABS: { type: SearchType; label: string }[] = [
  { type: "messages", label: "Messages" },
  { type: "channels", label: "Channels" },
  { type: "users", label: "Users" },
  { type: "files", label: "Files" },
];

const DEBOUNCE_MS = 300;

type SearchModalProps = {
  onClose: () => void;
  onJumpToChannel: (channelId: string) => void;
};

function MessageResultRow({ message, onClick }: { message: Message; onClick: () => void }) {
  const authorName = useUserName(message.sender_id);
  return (
    <button type="button" className={styles.resultRow} onClick={onClick}>
      <span className={styles.resultAuthor}>{authorName || "Someone"}</span>
      <span className={styles.resultSnippet}>{message.content}</span>
    </button>
  );
}

export function SearchModal({ onClose, onJumpToChannel }: SearchModalProps) {
  const [type, setType] = useState<SearchType>("messages");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = query.trim();
    if (!trimmed) {
      setResult(null);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setIsLoading(true);
      try {
        setResult(await runSearch(trimmed, type));
      } finally {
        setIsLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, type]);

  return (
    <Modal title="Search" onClose={onClose}>
      <input
        ref={inputRef}
        className={styles.input}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search messages, channels, people, files…"
      />

      <div className={styles.tabs}>
        {TABS.map((tab) => (
          <button
            key={tab.type}
            type="button"
            className={styles.tab}
            data-active={tab.type === type || undefined}
            onClick={() => setType(tab.type)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className={styles.results}>
        {isLoading ? (
          <div className={styles.hint}>Searching…</div>
        ) : !query.trim() ? (
          <div className={styles.hint}>Type to search across every conversation you're in.</div>
        ) : (
          <>
            {result?.type === "messages" &&
              (result.messages?.length ? (
                result.messages.map((m) => (
                  <MessageResultRow
                    key={m.id}
                    message={m}
                    onClick={() => m.channel_id && onJumpToChannel(m.channel_id)}
                  />
                ))
              ) : (
                <div className={styles.hint}>No messages found.</div>
              ))}
            {result?.type === "channels" &&
              (result.channels?.length ? (
                result.channels.map((c: Channel) => (
                  <button key={c.id} type="button" className={styles.resultRowFlex} onClick={() => onJumpToChannel(c.id)}>
                    <Avatar name={c.name} size={32} />
                    <span className={styles.resultPrimary}>#{c.name}</span>
                  </button>
                ))
              ) : (
                <div className={styles.hint}>No channels found.</div>
              ))}
            {result?.type === "users" &&
              (result.users?.length ? (
                result.users.map((u) => (
                  <div key={u.id} className={styles.resultRowFlex}>
                    <Avatar name={u.display_name} size={32} />
                    <div>
                      <div className={styles.resultPrimary}>{u.display_name}</div>
                      <div className={styles.resultSecondary}>{u.email}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className={styles.hint}>No users found.</div>
              ))}
            {result?.type === "files" &&
              (result.files?.length ? (
                result.files.map((f) => (
                  <div key={f.id} className={styles.resultRowFlex}>
                    <span className={styles.resultPrimary}>{f.file_name}</span>
                    <span className={styles.resultSecondary}>{f.mime_type}</span>
                  </div>
                ))
              ) : (
                <div className={styles.hint}>No files found.</div>
              ))}
          </>
        )}
      </div>
    </Modal>
  );
}
