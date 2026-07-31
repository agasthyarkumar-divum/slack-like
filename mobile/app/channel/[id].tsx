import { useLocalSearchParams } from "expo-router";

import { PlaceholderScreen } from "@/components/PlaceholderScreen";

export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  return (
    <PlaceholderScreen
      title={`Chat: ${id}`}
      subtitle="Virtualized message list + composer land in Phase 6 (architecture.md §3, §12)."
    />
  );
}
