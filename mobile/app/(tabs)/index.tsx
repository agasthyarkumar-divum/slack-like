import { useRouter } from "expo-router";
import { Plus } from "lucide-react-native";
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { Avatar } from "@/components/Avatar";
import { EmptyState } from "@/components/EmptyState";
import { Screen } from "@/components/Screen";
import { createChannel, listMyChannels } from "@/lib/api/channels";
import type { Channel } from "@/lib/api/types";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

export default function HomeScreen() {
  const { colors } = useTheme();
  const router = useRouter();
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
      router.push(`/channel/${channel.id}`);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Home</Text>
      </View>

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
          ListEmptyComponent={
            <EmptyState title="No channels yet." subtitle="Create one above to start talking." />
          }
          ItemSeparatorComponent={() => <View style={[styles.separator, { backgroundColor: colors.borderHairline }]} />}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => router.push(`/channel/${item.id}`)}
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
            >
              <Avatar name={item.name} size={44} />
              <View style={styles.rowText}>
                <Text style={[styles.channelName, { color: colors.textPrimary }]}>
                  {item.type === "dm" ? item.name : `#${item.name}`}
                </Text>
                <Text style={[styles.channelTopic, { color: colors.textSecondary }]} numberOfLines={1}>
                  {item.topic || "No topic set."}
                </Text>
              </View>
            </Pressable>
          )}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.sm },
  title: { fontFamily: fonts.display, fontSize: 28 },
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
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  rowText: { flex: 1, gap: 2 },
  channelName: { fontFamily: fonts.bodySemiBold, fontSize: 15 },
  channelTopic: { fontFamily: fonts.body, fontSize: 13 },
  separator: { height: 1, marginLeft: spacing.lg + 44 + spacing.md },
});
