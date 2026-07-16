import { useCallback, useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { Link, router, useFocusEffect } from "expo-router";
import { Search, UserPlus } from "lucide-react-native";
import { useTheme } from "@/theme";
import { listLocalBeneficiaries, searchBeneficiaries } from "@/lib/db/repo";
import type { LocalBeneficiary } from "@/lib/db/types";
import { useSync } from "@/lib/sync/SyncContext";
import { SyncBanner } from "@/components/SyncBanner";
import { ScreenBody } from "@/components/ui/Screen";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";

export default function BeneficiariesScreen() {
  const { colors, typography, spacing, radius, shadows } = useTheme();
  const { online, syncNow, refreshStatus } = useSync();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<LocalBeneficiary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = query.trim()
        ? await searchBeneficiaries(query)
        : await listLocalBeneficiaries();
      setItems(data);
    } finally {
      setLoading(false);
    }
  }, [query]);

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
      <View style={{ paddingHorizontal: spacing.screen, paddingTop: spacing.md, gap: spacing.md }}>
        <SyncBanner compact />
        <Input
          placeholder="Search by name, code, or phone"
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={() => void load()}
        />
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
          contentContainerStyle={{ padding: spacing.screen, paddingTop: 0, flexGrow: 1 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void onRefresh()} />}
          ListEmptyComponent={
            <EmptyState
              icon={<Search size={40} color={colors.textMuted} />}
              title="No beneficiaries yet"
              description={
                online
                  ? "Register your first beneficiary or pull to sync from the server."
                  : "Register beneficiaries offline — they will sync when you reconnect."
              }
              actionLabel="Register beneficiary"
              onAction={() => router.push("/register")}
            />
          }
          ListHeaderComponent={
            items.length === 0 ? null : (
              <Link href="/register" asChild>
                <Button
                  title="Register beneficiary"
                  icon={<UserPlus size={16} color={colors.textInverse} />}
                  fullWidth
                  style={{ marginBottom: spacing.md }}
                />
              </Link>
            )
          }
          renderItem={({ item }) => (
            <Link href={{ pathname: "/beneficiary/[id]", params: { id: item.local_id } }} asChild>
              <Pressable
                style={[
                  styles.card,
                  {
                    backgroundColor: colors.surface,
                    borderRadius: radius.lg,
                    borderColor: colors.borderLight,
                    padding: spacing.md,
                    marginBottom: spacing.sm,
                    ...shadows.sm,
                  },
                ]}
              >
                <View style={styles.row}>
                  <Text style={[typography.bodyMedium, { color: colors.text, flex: 1 }]}>
                    {item.first_name} {item.last_name}
                  </Text>
                  {item.sync_status !== "synced" && (
                    <Badge
                      label={item.sync_status}
                      variant={item.sync_status === "failed" ? "error" : "warning"}
                    />
                  )}
                </View>
                <Text style={[typography.caption, { color: colors.textMuted, marginTop: 4 }]}>
                  {item.code || "local"} · {item.phone || "no phone"} · {item.status}
                </Text>
              </Pressable>
            </Link>
          )}
        />
      )}
    </ScreenBody>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  card: { borderWidth: 1 },
});
