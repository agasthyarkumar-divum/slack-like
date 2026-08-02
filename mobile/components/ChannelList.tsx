import { Plus } from "lucide-react-native";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { EmptyState } from "@/components/EmptyState";
import { createChannel, listMembers, listMyChannels } from "@/lib/api/channels";
import { useUserName } from "@/lib/api/userDirectory";
import type { Channel } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";
import { useWS } from "@/lib/ws/WSContext";

function ChannelRow({ channel, active, onPress }: { channel: Channel; active: boolean; onPress: () => void }) {
  const { colors } = useTheme();
  const { user } = useAuth();
  const [otherUserId, setOtherUserId] = useState<string | null>(null);

  useEffect(() => {
    if (channel.type !== "dm") return undefined;
    let cancelled = false;
    listMembers(channel.id).then((members) => {
      if (cancelled) return;
      const other = members.find((m) => m.user_id !== user?.id);
      if (other) setOtherUserId(other.user_id);
    });
    return () => {
      cancelled = true;
    };
  }, [channel.id, channel.type, user?.id]);

  const dmName = useUserName(otherUserId);
  const isDM = channel.type === "dm";
  const displayName = isDM ? dmName || "Direct message" : channel.name;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        active && { backgroundColor: colors.accentMossSoft },
        pressed && !active && { opacity: 0.7 },
      ]}
    >
      <Avatar name={displayName} size={40} />
      <View style={styles.rowText}>
        <Text
          style={[styles.channelName, { color: active ? colors.accentMoss : colors.textPrimary }]}
          numberOfLines={1}
        >
          {isDM ? displayName : `#${channel.name}`}
        </Text>
        <Text style={[styles.channelTopic, { color: colors.textSecondary }]} numberOfLines={1}>
          {isDM ? "Direct message" : channel.topic || "No topic set."}
        </Text>
      </View>
      {channel.unread_count > 0 ? (
        <View style={[styles.badge, { backgroundColor: colors.accentMoss }]}>
          <Text style={styles.badgeText}>{channel.unread_count > 99 ? "99+" : channel.unread_count}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

type ChannelListProps = {
  activeChannelId?: string | null;
  onSelect: (channel: Channel) => void;
};

export function ChannelList({ activeChannelId, onSelect }: ChannelListProps) {
  const { colors } = useTheme();
  const { subscribe } = useWS();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [newChannelName, setNewChannelName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const loadChannels = useCallback(async () => {
    const data = await listMyChannels();
    setChannels(data);
  }, []);

  useEffect(() => {
    loadChannels().finally(() => setIsLoading(false));
  }, [loadChannels]);

  // New messages change unread counts for whichever channel they land in —
  // simplest correct refresh is to just re-fetch the list (cheap, infrequent).
  useEffect(() => subscribe("message.new", () => loadChannels()), [subscribe, loadChannels]);

  async function handleRefresh() {
    setIsRefreshing(true);
    await loadChannels();
    setIsRefreshing(false);
  }

  async function handleCreateChannel() {
    const name = newChannelName.trim();
    if (!name) return;
    setIsCreating(true);
    try {
      const channel = await createChannel({ name, type: "public" });
      setNewChannelName("");
      setChannels((prev) => [channel, ...prev]);
      onSelect(channel);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <View style={styles.container}>
      <View style={[styles.composer, { borderColor: colors.borderHairline }]}>
        <TextInput
          value={newChannelName}
          onChangeText={setNewChannelName}
          placeholder="New channel name…"
          placeholderTextColor={colors.textSecondary}
          style={[styles.composerInput, { color: colors.textPrimary }]}
          onSubmitEditing={handleCreateChannel}
          returnKeyType="done"
        />
        <Pressable
          onPress={handleCreateChannel}
          disabled={isCreating || !newChannelName.trim()}
          accessibilityRole="button"
          accessibilityLabel="Create channel"
          style={[
            styles.composerButton,
            { backgroundColor: colors.accentMoss, opacity: newChannelName.trim() ? 1 : 0.5 },
          ]}
        >
          {isCreating ? <ActivityIndicator size="small" color="#FFF" /> : <Plus size={18} color="#FFF" strokeWidth={1.5} />}
        </Pressable>
      </View>

      {isLoading ? (
        <ActivityIndicator style={styles.loading} color={colors.accentMoss} />
      ) : (
        <FlatList
          data={channels}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} tintColor={colors.accentMoss} />}
          ListEmptyComponent={<EmptyState title="No channels yet." subtitle="Create one above to start talking." />}
          ItemSeparatorComponent={() => <View style={[styles.separator, { backgroundColor: colors.borderHairline }]} />}
          renderItem={({ item }) => (
            <ChannelRow channel={item} active={item.id === activeChannelId} onPress={() => onSelect(item)} />
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  composer: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingLeft: spacing.md,
    gap: spacing.sm,
  },
  composerInput: { flex: 1, fontFamily: fonts.body, fontSize: 15, paddingVertical: spacing.sm + 2 },
  composerButton: {
    width: 36,
    height: 36,
    borderRadius: radii.sm,
    alignItems: "center",
    justifyContent: "center",
    margin: 4,
  },
  loading: { marginTop: spacing.xxl },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderRadius: radii.sm },
  rowText: { flex: 1, gap: 2 },
  channelName: { fontFamily: fonts.bodySemiBold, fontSize: 15 },
  channelTopic: { fontFamily: fonts.body, fontSize: 13 },
  separator: { height: 1, marginLeft: spacing.lg + 40 + spacing.md },
  badge: { minWidth: 22, height: 22, borderRadius: radii.pill, alignItems: "center", justifyContent: "center", paddingHorizontal: 6 },
  badgeText: { color: "#FFF", fontFamily: fonts.bodySemiBold, fontSize: 12 },
});
