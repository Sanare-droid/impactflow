import { useCallback, useState } from "react";
import { RefreshControl, StyleSheet, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { UserPlus, ClipboardList, RefreshCw } from "lucide-react-native";
import { useTheme } from "@/theme";
import {
  countBeneficiaries,
  countLocalSurveys,
  countOpenTasks,
  countUnreadNotifications,
  queueCounts,
} from "@/lib/db/repo";
import { useSync } from "@/lib/sync/SyncContext";
import { SyncBanner } from "@/components/SyncBanner";
import { Screen } from "@/components/ui/Screen";
import { KpiCard } from "@/components/ui/KpiCard";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { Text } from "react-native";

export default function DashboardScreen() {
  const { colors, typography, spacing } = useTheme();
  const { online, syncNow, refreshStatus } = useSync();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({
    beneficiaries: 0,
    surveys: 0,
    tasks: 0,
    notifications: 0,
    pending: 0,
    failed: 0,
  });

  const load = useCallback(async () => {
    try {
      const [beneficiaries, surveys, tasks, notifications, queue] = await Promise.all([
        countBeneficiaries(),
        countLocalSurveys(),
        countOpenTasks(),
        countUnreadNotifications(),
        queueCounts(),
      ]);
      setStats({
        beneficiaries,
        surveys,
        tasks,
        notifications,
        pending: queue.pending,
        failed: queue.failed,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
      void refreshStatus();
    }, [load, refreshStatus]),
  );

  async function onRefresh() {
    setRefreshing(true);
    try {
      if (online) await syncNow();
      await load();
      await refreshStatus();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <Screen
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void onRefresh()} />}
    >
      <Text style={[typography.display, { color: colors.primaryDark, fontSize: 28 }]}>Dashboard</Text>
      <Text style={[typography.body, { color: colors.textMuted, marginBottom: spacing.md }]}>
        Field overview & sync status
      </Text>

      <SyncBanner />

      <SectionHeader title="Key metrics" subtitle="Cached locally — sync to refresh" />
      {loading ? (
        <View style={styles.kpiRow}>
          <SkeletonCard />
          <SkeletonCard />
        </View>
      ) : (
        <View style={styles.kpiRow}>
          <KpiCard label="Beneficiaries" value={stats.beneficiaries} />
          <KpiCard label="Open tasks" value={stats.tasks} />
        </View>
      )}
      {!loading && (
        <View style={[styles.kpiRow, { marginTop: spacing.md }]}>
          <KpiCard label="Surveys" value={stats.surveys} />
          <KpiCard label="Unread" value={stats.notifications} subtitle="notifications" />
        </View>
      )}

      <SectionHeader title="Quick actions" />
      <View style={styles.actions}>
        <Card padding="md" style={styles.actionCard} onPress={() => router.push("/register")}>
          <UserPlus size={22} color={colors.primary} />
          <Text style={[typography.bodyMedium, { color: colors.text, marginTop: spacing.sm }]}>
            Register beneficiary
          </Text>
          <Text style={[typography.caption, { color: colors.textMuted }]}>Works offline</Text>
        </Card>
        <Card padding="md" style={styles.actionCard} onPress={() => router.push("/surveys")}>
            <ClipboardList size={22} color={colors.primary} />
            <Text style={[typography.bodyMedium, { color: colors.text, marginTop: spacing.sm }]}>
              Capture survey
            </Text>
            <Text style={[typography.caption, { color: colors.textMuted }]}>Published forms</Text>
        </Card>
      </View>

      {(stats.pending > 0 || stats.failed > 0) && (
        <View style={{ marginTop: spacing.lg }}>
          <Button
            title={online ? "Sync now" : "Waiting for connection"}
            icon={<RefreshCw size={16} color={colors.textInverse} />}
            onPress={() => void syncNow()}
            disabled={!online}
            fullWidth
            variant={stats.failed > 0 ? "danger" : "primary"}
          />
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiRow: { flexDirection: "row", gap: 12 },
  actions: { flexDirection: "row", gap: 12 },
  actionCard: { flex: 1 },
});
