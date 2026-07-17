import { useCallback, useState } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useFocusEffect } from "expo-router";
import { CheckSquare, Calendar, Circle, CheckCircle2 } from "lucide-react-native";
import { useTheme } from "@/theme";
import { getMeta } from "@/lib/db";
import { listLocalTasks, updateLocalTaskStatus } from "@/lib/db/repo";
import type { LocalTask } from "@/lib/db/types";
import { useSync } from "@/lib/sync/SyncContext";
import { SyncBanner } from "@/components/SyncBanner";
import { ScreenBody } from "@/components/ui/Screen";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Card } from "@/components/ui/Card";
import { SkeletonCard } from "@/components/ui/Skeleton";

function priorityVariant(priority: string | null): "default" | "warning" | "error" | "info" {
  if (priority === "high" || priority === "urgent") return "error";
  if (priority === "medium") return "warning";
  if (priority === "low") return "info";
  return "default";
}

export default function TasksScreen() {
  const { colors, typography, spacing } = useTheme();
  const { online, syncNow, refreshStatus } = useSync();
  const [items, setItems] = useState<LocalTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [everSynced, setEverSynced] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await listLocalTasks());
      const last = await getMeta("last_sync_at");
      setEverSynced(Boolean(last));
    } finally {
      setLoading(false);
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

  async function toggleComplete(item: LocalTask) {
    if (busyId) return;
    const next = item.status === "done" ? "open" : "done";
    setBusyId(item.local_id);
    try {
      await updateLocalTaskStatus(item.local_id, next);
      await load();
      if (online) {
        await syncNow();
        await refreshStatus();
        await load();
      }
    } finally {
      setBusyId(null);
    }
  }

  const emptyTitle = everSynced ? "No tasks assigned" : "Not synced yet";
  const emptyDescription = everSynced
    ? "Tasks assigned to you on the web (Projects or Tasks) appear here after sync. Pull to refresh when online."
    : "Pull to refresh while online to download tasks assigned to you.";

  return (
    <ScreenBody>
      <View style={{ paddingHorizontal: spacing.screen, paddingTop: spacing.md }}>
        <SyncBanner compact />
      </View>
      {loading ? (
        <View style={{ padding: spacing.screen }}>
          <SkeletonCard />
          <SkeletonCard />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.local_id}
          contentContainerStyle={{ padding: spacing.screen, flexGrow: 1 }}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => void onRefresh()} />
          }
          ListEmptyComponent={
            <EmptyState
              icon={<CheckSquare size={40} color={colors.textMuted} />}
              title={emptyTitle}
              description={emptyDescription}
            />
          }
          renderItem={({ item }) => {
            const done = item.status === "done";
            return (
              <Card padding="md" style={{ marginBottom: spacing.sm }}>
                <View style={styles.row}>
                  <Pressable
                    onPress={() => void toggleComplete(item)}
                    disabled={busyId === item.local_id}
                    hitSlop={8}
                    accessibilityRole="button"
                    accessibilityLabel={done ? "Mark task open" : "Mark task complete"}
                  >
                    {done ? (
                      <CheckCircle2 size={22} color={colors.success} />
                    ) : (
                      <Circle size={22} color={colors.textMuted} />
                    )}
                  </Pressable>
                  <Text
                    style={[
                      typography.bodyMedium,
                      {
                        color: colors.text,
                        flex: 1,
                        textDecorationLine: done ? "line-through" : "none",
                        opacity: done ? 0.7 : 1,
                      },
                    ]}
                  >
                    {item.title}
                  </Text>
                  <Badge
                    label={item.sync_status === "pending" ? "pending sync" : item.status}
                    variant={done ? "success" : "default"}
                  />
                </View>
                {item.description ? (
                  <Text
                    style={[typography.caption, { color: colors.textMuted, marginTop: spacing.xs }]}
                    numberOfLines={2}
                  >
                    {item.description}
                  </Text>
                ) : null}
                <View style={[styles.meta, { marginTop: spacing.sm }]}>
                  {item.priority ? (
                    <Badge label={item.priority} variant={priorityVariant(item.priority)} />
                  ) : null}
                  {item.due_date ? (
                    <View style={styles.metaItem}>
                      <Calendar size={12} color={colors.textMuted} />
                      <Text style={[typography.caption, { color: colors.textMuted }]}>
                        {new Date(item.due_date).toLocaleDateString()}
                      </Text>
                    </View>
                  ) : null}
                </View>
              </Card>
            );
          }}
        />
      )}
    </ScreenBody>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  meta: { flexDirection: "row", alignItems: "center", gap: 8 },
  metaItem: { flexDirection: "row", alignItems: "center", gap: 4 },
});
