import { useEffect, useState } from "react";
import { LogOut, Settings } from "lucide-react";

import { Avatar } from "@/components/Avatar";
import { listMembers } from "@/lib/api/channels";
import { useUserName } from "@/lib/api/userDirectory";
import { useAuth } from "@/lib/auth/AuthContext";
import type { Channel } from "@/lib/api/types";
import styles from "./Sidebar.module.css";

type SidebarProps = {
  channels: Channel[];
  activeChannelId: string | null;
  onSelect: (channel: Channel) => void;
  presence: Record<string, string>;
  onOpenSettings: () => void;
};

function useDmOtherUserId(channel: Channel): string | null {
  const { user } = useAuth();
  const [otherId, setOtherId] = useState<string | null>(null);

  useEffect(() => {
    if (channel.type !== "dm") return;
    let cancelled = false;
    listMembers(channel.id).then((members) => {
      if (cancelled) return;
      const other = members.find((m) => m.user_id !== user?.id);
      if (other) setOtherId(other.user_id);
    });
    return () => {
      cancelled = true;
    };
  }, [channel.id, channel.type, user?.id]);

  return otherId;
}

function ChannelRow({
  channel,
  active,
  onSelect,
}: {
  channel: Channel;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button type="button" className={styles.row} data-active={active || undefined} onClick={onSelect}>
      <span className={styles.hash}>#</span>
      <span className={styles.rowName}>{channel.name}</span>
      {channel.unread_count > 0 ? <span className={styles.badge}>{channel.unread_count}</span> : null}
    </button>
  );
}

function DmRow({
  channel,
  active,
  presence,
  onSelect,
}: {
  channel: Channel;
  active: boolean;
  presence: Record<string, string>;
  onSelect: () => void;
}) {
  const otherId = useDmOtherUserId(channel);
  const name = useUserName(otherId);
  const status = otherId ? presence[otherId] : undefined;

  return (
    <button type="button" className={styles.row} data-active={active || undefined} onClick={onSelect}>
      <span className={styles.dmAvatar}>
        <Avatar name={name || "?"} size={22} />
        <span className={styles.presenceDot} data-online={status === "online" || undefined} />
      </span>
      <span className={styles.rowName}>{name || "Direct message"}</span>
      {channel.unread_count > 0 ? <span className={styles.badge}>{channel.unread_count}</span> : null}
    </button>
  );
}

export function Sidebar({ channels, activeChannelId, onSelect, presence, onOpenSettings }: SidebarProps) {
  const { user, logout } = useAuth();
  const channelList = channels.filter((c) => c.type !== "dm");
  const dmList = channels.filter((c) => c.type === "dm");

  return (
    <aside className={styles.sidebar}>
      <div className={styles.workspaceHeader}>
        <div className={styles.workspaceMark}>DC</div>
        <span className={styles.workspaceName}>Divum Chat</span>
      </div>

      <nav className={styles.nav}>
        <div className={styles.section}>
          <span className={styles.sectionLabel}>Channels</span>
          {channelList.map((c) => (
            <ChannelRow key={c.id} channel={c} active={c.id === activeChannelId} onSelect={() => onSelect(c)} />
          ))}
        </div>

        <div className={styles.section}>
          <span className={styles.sectionLabel}>Direct messages</span>
          {dmList.map((c) => (
            <DmRow
              key={c.id}
              channel={c}
              active={c.id === activeChannelId}
              presence={presence}
              onSelect={() => onSelect(c)}
            />
          ))}
        </div>
      </nav>

      <div className={styles.footer}>
        <Avatar name={user?.display_name ?? "?"} size={32} />
        <span className={styles.userName}>{user?.display_name}</span>
        <button type="button" className={styles.iconButton} aria-label="Settings" onClick={onOpenSettings}>
          <Settings size={16} strokeWidth={1.5} />
        </button>
        <button type="button" className={styles.iconButton} aria-label="Log out" onClick={logout}>
          <LogOut size={16} strokeWidth={1.5} />
        </button>
      </div>
    </aside>
  );
}
