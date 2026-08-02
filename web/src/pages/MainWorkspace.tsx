import { useEffect, useState } from "react";

import { ConversationPane } from "@/components/ConversationPane";
import { SearchModal } from "@/components/SearchModal";
import { SettingsModal } from "@/components/SettingsModal";
import { Sidebar } from "@/components/Sidebar";
import { ThreadPanel } from "@/components/ThreadPanel";
import { listMyChannels } from "@/lib/api/channels";
import { useWS } from "@/lib/ws/WSContext";
import type { Channel, Message } from "@/lib/api/types";
import styles from "./MainWorkspace.module.css";

export default function MainWorkspace() {
  const { subscribe } = useWS();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [activeChannelId, setActiveChannelId] = useState<string | null>(null);
  const [threadMessage, setThreadMessage] = useState<Message | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [presence, setPresence] = useState<Record<string, string>>({});

  useEffect(() => {
    listMyChannels().then((data) => {
      setChannels(data);
      if (data.length > 0) setActiveChannelId((prev) => prev ?? data[0].id);
    });
  }, []);

  // New messages change unread counts for whichever channel they land in —
  // simplest correct refresh is to just re-fetch the list (cheap, infrequent).
  useEffect(
    () =>
      subscribe("message.new", (data) => {
        if (data.channel_id === activeChannelId) return; // already visible, no unread to clear
        listMyChannels().then(setChannels);
      }),
    [subscribe, activeChannelId]
  );

  useEffect(
    () =>
      subscribe("presence.update", (data) => {
        setPresence((prev) => ({ ...prev, [data.user_id as string]: data.status as string }));
      }),
    [subscribe]
  );

  function handleSelectChannel(channel: Channel) {
    setActiveChannelId(channel.id);
    setThreadMessage(null);
    setChannels((prev) => prev.map((c) => (c.id === channel.id ? { ...c, unread_count: 0 } : c)));
  }

  function handleJumpToChannel(channelId: string) {
    setSearchOpen(false);
    setActiveChannelId(channelId);
    setThreadMessage(null);
  }

  const activeChannel = channels.find((c) => c.id === activeChannelId) ?? null;

  return (
    <div className={styles.workspace}>
      <Sidebar
        channels={channels}
        activeChannelId={activeChannelId}
        onSelect={handleSelectChannel}
        presence={presence}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {activeChannel ? (
        <ConversationPane
          key={activeChannel.id}
          channel={activeChannel}
          presence={presence}
          onOpenThread={setThreadMessage}
          onOpenSearch={() => setSearchOpen(true)}
          onOpenSettings={() => setSettingsOpen(true)}
        />
      ) : (
        <div className={styles.emptyMain}>No channels yet.</div>
      )}

      {threadMessage ? (
        <ThreadPanel
          key={threadMessage.id}
          message={threadMessage}
          onClose={() => setThreadMessage(null)}
          onParentUpdate={setThreadMessage}
        />
      ) : null}

      {searchOpen ? <SearchModal onClose={() => setSearchOpen(false)} onJumpToChannel={handleJumpToChannel} /> : null}
      {settingsOpen ? <SettingsModal onClose={() => setSettingsOpen(false)} /> : null}
    </div>
  );
}
