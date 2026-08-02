import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { EmptyState } from "@/components/EmptyState";
import { Screen } from "@/components/Screen";
import { startDM } from "@/lib/api/channels";
import { search as runSearch } from "@/lib/api/search";
import type { SearchResponse, SearchType } from "@/lib/api/types";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

const TABS: { type: SearchType; label: string }[] = [
  { type: "messages", label: "Messages" },
  { type: "channels", label: "Channels" },
  { type: "users", label: "Users" },
  { type: "files", label: "Files" },
];

const DEBOUNCE_MS = 350;

export default function SearchScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const [type, setType] = useState<SearchType>("messages");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [startingDmFor, setStartingDmFor] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function handleStartDM(userId: string) {
    setStartingDmFor(userId);
    try {
      const channel = await startDM(userId);
      router.push(`/channel/${channel.id}`);
    } finally {
      setStartingDmFor(null);
    }
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = query.trim();
    if (!trimmed) {
      setResult(null);
      return undefined;
    }
    debounceRef.current = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await runSearch(trimmed, type);
        setResult(data);
      } finally {
        setIsLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, type]);

  const items = result
    ? result.type === "messages"
      ? result.messages ?? []
      : result.type === "channels"
        ? result.channels ?? []
        : result.type === "users"
          ? result.users ?? []
          : result.files ?? []
    : [];

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Search</Text>
      </View>

      <TextInput
        value={query}
        onChangeText={setQuery}
        placeholder="Search…"
        placeholderTextColor={colors.textSecondary}
        style={[
          styles.input,
          { backgroundColor: colors.bgSurface, color: colors.textPrimary, borderColor: colors.borderHairline },
        ]}
        autoCapitalize="none"
        autoFocus
      />

      <View style={styles.tabRow}>
        {TABS.map((tab) => {
          const isActive = tab.type === type;
          return (
            <Pressable
              key={tab.type}
              onPress={() => setType(tab.type)}
              style={[
                styles.tab,
                { backgroundColor: isActive ? colors.accentMossSoft : "transparent" },
              ]}
            >
              <Text
                style={[
                  styles.tabLabel,
                  { color: isActive ? colors.accentMoss : colors.textSecondary },
                ]}
              >
                {tab.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {isLoading ? (
        <ActivityIndicator style={styles.loading} color={colors.accentMoss} />
      ) : !query.trim() ? (
        <EmptyState title="Search Divum Chat" subtitle="Messages, channels, people, and files." />
      ) : items.length === 0 ? (
        <EmptyState title="Nothing found." subtitle="Try a different word." />
      ) : (
        <ScrollView contentContainerStyle={styles.results}>
          {result?.type === "messages" &&
            result.messages?.map((m) => (
              <Pressable
                key={m.id}
                onPress={() => m.channel_id && router.push(`/channel/${m.channel_id}`)}
                style={[styles.resultRow, { borderColor: colors.borderHairline }]}
              >
                <Text style={[styles.resultPrimary, { color: colors.textPrimary }]} numberOfLines={2}>
                  {m.content}
                </Text>
              </Pressable>
            ))}
          {result?.type === "channels" &&
            result.channels?.map((c) => (
              <Pressable
                key={c.id}
                onPress={() => router.push(`/channel/${c.id}`)}
                style={[styles.resultRow, styles.resultRowFlex, { borderColor: colors.borderHairline }]}
              >
                <Avatar name={c.name} size={36} />
                <Text style={[styles.resultPrimary, { color: colors.textPrimary }]}>#{c.name}</Text>
              </Pressable>
            ))}
          {result?.type === "users" &&
            result.users?.map((u) => (
              <Pressable
                key={u.id}
                onPress={() => handleStartDM(u.id)}
                disabled={startingDmFor === u.id}
                style={[styles.resultRow, styles.resultRowFlex, { borderColor: colors.borderHairline }]}
              >
                <Avatar name={u.display_name} size={36} />
                <View style={styles.flexOne}>
                  <Text style={[styles.resultPrimary, { color: colors.textPrimary }]}>{u.display_name}</Text>
                  <Text style={[styles.resultSecondary, { color: colors.textSecondary }]}>{u.email}</Text>
                </View>
                {startingDmFor === u.id ? <ActivityIndicator size="small" color={colors.accentMoss} /> : null}
              </Pressable>
            ))}
          {result?.type === "files" &&
            result.files?.map((f) => (
              <View key={f.id} style={[styles.resultRow, { borderColor: colors.borderHairline }]}>
                <Text style={[styles.resultPrimary, { color: colors.textPrimary }]}>{f.file_name}</Text>
                <Text style={[styles.resultSecondary, { color: colors.textSecondary }]}>{f.mime_type}</Text>
              </View>
            ))}
        </ScrollView>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  title: { fontFamily: fonts.display, fontSize: 28, marginBottom: spacing.md },
  input: {
    marginHorizontal: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
    fontFamily: fonts.body,
    fontSize: 15,
  },
  tabRow: { flexDirection: "row", gap: spacing.xs, paddingHorizontal: spacing.lg, marginVertical: spacing.md },
  tab: { paddingVertical: 6, paddingHorizontal: spacing.sm + 2, borderRadius: radii.pill },
  tabLabel: { fontFamily: fonts.bodyMedium, fontSize: 13 },
  loading: { marginTop: spacing.xxl },
  results: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl, gap: spacing.sm },
  resultRow: { paddingVertical: spacing.sm + 2, borderBottomWidth: 1 },
  resultRowFlex: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  flexOne: { flex: 1 },
  resultPrimary: { fontFamily: fonts.bodyMedium, fontSize: 14 },
  resultSecondary: { fontFamily: fonts.body, fontSize: 12 },
});
