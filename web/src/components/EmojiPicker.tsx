import { useEffect, useRef } from "react";

import styles from "./EmojiPicker.module.css";

// A fixed curated set rather than a full emoji-picker dependency — plenty for
// an internal team chat's reactions, and keeps the bundle (and the UI) small.
export const CURATED_EMOJI = ["👍", "❤️", "😂", "🎉", "👀", "🙏", "🔥", "✅"];

type EmojiPickerProps = {
  onSelect: (emoji: string) => void;
  onClose: () => void;
};

export function EmojiPicker({ onSelect, onClose }: EmojiPickerProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onPointerDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  return (
    <div ref={ref} className={styles.popover} role="menu">
      {CURATED_EMOJI.map((emoji) => (
        <button
          key={emoji}
          type="button"
          className={styles.emoji}
          role="menuitem"
          onClick={() => {
            onSelect(emoji);
            onClose();
          }}
        >
          {emoji}
        </button>
      ))}
    </div>
  );
}
