import { useCallback, useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { Link, useFocusEffect } from "expo-router";
import { ClipboardList } from "lucide-react-native";
import { useTheme } from "@/theme";
import { listLocalSurveys } from "@/lib/db/repo";
import type { LocalSurvey } from "@/lib/db/types";
import { useSync } from "@/lib/sync/SyncContext";
import { SyncBanner } from "@/components/SyncBanner";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenBody } from "@/components/ui/Screen";

export default function SurveysScreen() {
  const { colors, typography, spacing, radius, shadows } = useTheme();
  const [items, setItems] = useState<LocalSurvey[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const { online, syncNow, refreshStatus } = useSync();

  const load = useCallback(async () => {
    setItems(await listLocalSurveys());
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
    <ScreenBody>
      <View style={{ paddingHorizontal: spacing.screen, paddingTop: spacing.md }}>
        <SyncBanner compact />
      </View>
      <FlatList
        contentContainerStyle={{ padding: spacing.screen, flexGrow: 1 }}
        data={items}
        keyExtractor={(item) => item.local_id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void onRefresh()} />}
        ListEmptyComponent={
          <EmptyState
            icon={<ClipboardList size={40} color={colors.textMuted} />}
            title="No surveys downloaded"
            description={
              online
                ? "Pull to refresh and sync published forms for offline capture."
                : "Connect once to download survey forms for offline use."
            }
          />
        }
        renderItem={({ item }) => (
          <Link href={{ pathname: "/surveys/[id]", params: { id: item.local_id } }} asChild>
            <Pressable
              style={[
                styles.card,
                {
                  backgroundColor: colors.surface,
                  borderRadius: radius.lg,
                  borderColor: colors.borderLight,
                  padding: spacing.lg,
                  marginBottom: spacing.sm,
                  ...shadows.sm,
                },
              ]}
            >
              <Text style={[typography.title, { color: colors.text }]}>{item.name}</Text>
              <Text style={[typography.caption, { color: colors.textMuted, marginTop: 4 }]}>
                {item.code || "—"} · v{item.current_version}
              </Text>
            </Pressable>
          </Link>
        )}
      />
    </ScreenBody>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1 },
});
