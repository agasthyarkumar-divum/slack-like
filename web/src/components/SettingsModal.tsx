import { useState } from "react";

import { Modal } from "@/components/Modal";
import { updateSettings } from "@/lib/api/users";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import type { NotificationPreference } from "@/lib/api/types";
import styles from "./SettingsModal.module.css";

const NOTIFICATION_OPTIONS: { value: NotificationPreference; label: string; description: string }[] = [
  { value: "all", label: "All", description: "Every mention, DM, and reaction." },
  { value: "mentions_dms", label: "Mentions & DMs", description: "Skip reaction notifications." },
  { value: "none", label: "Nothing", description: "Turn off in-app notifications." },
];

type SettingsModalProps = {
  onClose: () => void;
};

export function SettingsModal({ onClose }: SettingsModalProps) {
  const { mode, setMode } = useTheme();
  const { user, refreshUser } = useAuth();
  const [preference, setPreference] = useState<NotificationPreference>(
    user?.notification_preference ?? "all"
  );
  const [isSaving, setIsSaving] = useState(false);

  async function handlePreferenceChange(next: NotificationPreference) {
    setPreference(next);
    setIsSaving(true);
    try {
      await updateSettings(next);
      await refreshUser();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal title="Settings" onClose={onClose}>
      <section className={styles.section}>
        <h3 className={styles.sectionLabel}>Appearance</h3>
        <div className={styles.segmented}>
          {(["light", "dark"] as const).map((option) => (
            <button
              key={option}
              type="button"
              className={styles.segment}
              data-active={mode === option || undefined}
              onClick={() => setMode(option)}
            >
              {option === "light" ? "Light" : "Dark"}
            </button>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h3 className={styles.sectionLabel}>Notifications</h3>
        <div className={styles.radioGroup} role="radiogroup" aria-label="Notification preference">
          {NOTIFICATION_OPTIONS.map((option) => (
            <label key={option.value} className={styles.radioRow}>
              <input
                type="radio"
                name="notification_preference"
                checked={preference === option.value}
                disabled={isSaving}
                onChange={() => handlePreferenceChange(option.value)}
              />
              <span className={styles.radioText}>
                <span className={styles.radioLabel}>{option.label}</span>
                <span className={styles.radioDescription}>{option.description}</span>
              </span>
            </label>
          ))}
        </div>
      </section>
    </Modal>
  );
}
