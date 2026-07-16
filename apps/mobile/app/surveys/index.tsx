import { useCallback, useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { Link, useFocusEffect } from "expo-router";
import { listLocalSurveys } from "@/lib/db/repo";
import type { LocalSurvey } from "@/lib/db/types";
import { useSync } from "@/lib/sync/SyncContext";
import { SyncBanner } from "@/components/SyncBanner";

export default function SurveysScreen() {
  const [items, setItems] = useState<LocalSurvey[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { online, syncNow, refreshStatus } = useSync();

  const load = useCallback(async () => {
    try {
      setItems(await listLocalSurveys());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load surveys");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function onRefresh() {
    setRefreshing(true);
    try {
      if (online) {
        await syncNow();
        await refreshStatus();
      }
      await load();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <View style={styles.container}>
      <SyncBanner />
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        contentContainerStyle={{ padding: 20, gap: 10 }}
        data={items}
        keyExtractor={(item) => item.local_id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => void onRefresh()} />
        }
        ListEmptyComponent={
          <Text style={styles.muted}>
            {online
              ? "No published surveys yet. Pull to refresh."
              : "No surveys downloaded yet — connect once to sync forms for offline use."}
          </Text>
        }
        renderItem={({ item }) => (
          <Link href={{ pathname: "/surveys/[id]", params: { id: item.local_id } }} asChild>
            <Pressable style={styles.card}>
              <Text style={styles.cardTitle}>{item.name}</Text>
              <Text style={styles.muted}>
                {item.code || "—"} · v{item.current_version}
              </Text>
            </Pressable>
          </Link>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#FAFAF9" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#F5F5F4",
  },
  cardTitle: { fontWeight: "600", color: "#1C1917", marginBottom: 4, fontSize: 16 },
  muted: { color: "#78716C", fontSize: 13 },
  error: { color: "#E11D48", paddingHorizontal: 20, paddingTop: 8 },
});
