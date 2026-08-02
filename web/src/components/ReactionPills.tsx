import type { ReactionSummary } from "@/lib/api/types";
import styles from "./ReactionPills.module.css";

type ReactionPillsProps = {
  reactions: ReactionSummary[];
  onToggle: (emoji: string) => void;
};

export function ReactionPills({ reactions, onToggle }: ReactionPillsProps) {
  if (reactions.length === 0) return null;

  return (
    <div className={styles.row}>
      {reactions.map((r) => (
        <button
          key={r.emoji}
          type="button"
          className={styles.pill}
          data-active={r.me || undefined}
          onClick={() => onToggle(r.emoji)}
          aria-pressed={r.me}
        >
          <span>{r.emoji}</span>
          <span className={styles.count}>{r.count}</span>
        </button>
      ))}
    </div>
  );
}
