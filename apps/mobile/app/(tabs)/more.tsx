import { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { Bell, History, LogOut, Settings, Smartphone } from "lucide-react-native";
import { useTheme } from "@/theme";
import { useAuth } from "@/lib/auth/AuthContext";
import { useSync } from "@/lib/sync/SyncContext";
import { getAppVersion, getDeviceId } from "@/lib/device";
import { listLocalNotifications, listSyncLogs, markNotificationRead } from "@/lib/db/repo";
import type { LocalNotification, SyncLogRow } from "@/lib/db/types";
import { Screen } from "@/components/ui/Screen";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function MoreScreen() {
  const { colors, typography, spacing } = useTheme();
  const { signOut } = useAuth();
  const { online, lastSyncAt, pending, failed, syncNow } = useSync();
  const [notifications, setNotifications] = useState<LocalNotification[]>([]);
  const [logs, setLogs] = useState<SyncLogRow[]>([]);
  const [deviceId, setDeviceIdState] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const load = useCallback(async () => {
    setNotifications(await listLocalNotifications(true));
    setLogs(await listSyncLogs(15));
    setDeviceIdState(await getDeviceId());
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  async function onMarkRead(localId: string) {
    await markNotificationRead(localId);
    await load();
  }

  function formatWhen(iso: string | null): string {
    if (!iso) return "Never";
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  return (
    <Screen>
      <Text style={[typography.display, { color: colors.primaryDark, fontSize: 28 }]}>More</Text>
      <Text style={[typography.body, { color: colors.textMuted, marginBottom: spacing.lg }]}>
        Settings, notifications & sync history
      </Text>

      <SectionHeader title="Device" />
      <Card padding="md" style={{ marginBottom: spacing.lg }}>
        <View style={styles.row}>
          <Smartphone size={20} color={colors.primary} />
          <View style={{ flex: 1, marginLeft: spacing.sm }}>
            <Text style={[typography.bodyMedium, { color: colors.text }]}>This device</Text>
            <Text style={[typography.caption, { color: colors.textMuted }]}>
              v{getAppVersion()} · {online ? "Online" : "Offline"}
            </Text>
            {deviceId ? (
              <Text style={[typography.caption, { color: colors.textMuted }]} numberOfLines={1}>
                ID {deviceId.slice(0, 8)}…
              </Text>
            ) : null}
          </View>
        </View>
        <Text style={[typography.caption, { color: colors.textMuted, marginTop: spacing.sm }]}>
          Last sync: {formatWhen(lastSyncAt)}
          {pending > 0 ? ` · ${pending} pending` : ""}
          {failed > 0 ? ` · ${failed} failed` : ""}
        </Text>
        <View style={{ marginTop: spacing.md }}>
          <Button title="Sync now" onPress={() => void syncNow()} disabled={!online} fullWidth variant="secondary" />
        </View>
      </Card>

      <SectionHeader
        title="Notifications"
        subtitle="Cached from server — read-only inbox"
        actionLabel={notifications.length ? "Mark all read" : undefined}
        onAction={
          notifications.length
            ? () => {
                void Promise.all(notifications.map((n) => markNotificationRead(n.local_id))).then(load);
              }
            : undefined
        }
      />
      {notifications.length === 0 ? (
        <Card padding="md">
          <View style={styles.row}>
            <Bell size={18} color={colors.textMuted} />
            <Text style={[typography.body, { color: colors.textMuted, marginLeft: spacing.sm }]}>
              No unread notifications
            </Text>
          </View>
        </Card>
      ) : (
        notifications.slice(0, 5).map((n) => (
          <Card key={n.local_id} padding="md" style={{ marginBottom: spacing.sm }} onPress={() => void onMarkRead(n.local_id)}>
            <Text style={[typography.bodyMedium, { color: colors.text }]}>{n.title}</Text>
            {n.body ? (
              <Text style={[typography.caption, { color: colors.textMuted, marginTop: 4 }]} numberOfLines={2}>
                {n.body}
              </Text>
            ) : null}
          </Card>
        ))
      )}

      <SectionHeader
        title="Sync history"
        actionLabel={showHistory ? "Hide" : "Show"}
        onAction={() => setShowHistory((v) => !v)}
      />
      {showHistory && (
        <FlatList
          data={logs}
          scrollEnabled={false}
          keyExtractor={(item) => item.id}
          ListEmptyComponent={
            <Text style={[typography.caption, { color: colors.textMuted }]}>No sync sessions yet</Text>
          }
          renderItem={({ item }) => (
            <Card padding="md" style={{ marginBottom: spacing.sm }}>
              <View style={styles.row}>
                <History size={16} color={colors.textMuted} />
                <Text style={[typography.caption, { color: colors.textSecondary, flex: 1, marginLeft: spacing.sm }]}>
                  {new Date(item.started_at).toLocaleString()}
                </Text>
                <Badge
                  label={item.status}
                  variant={item.status === "failed" ? "error" : item.status === "conflict" ? "warning" : "success"}
                />
              </View>
              <Text style={[typography.caption, { color: colors.textMuted, marginTop: 4 }]}>
                ↑{item.pushed_count} ↓{item.pulled_count}
                {item.failed_count > 0 ? ` · ${item.failed_count} failed` : ""}
                {item.conflict_count > 0 ? ` · ${item.conflict_count} conflicts` : ""}
              </Text>
            </Card>
          )}
        />
      )}

      <SectionHeader title="Account" />
      <Card padding="md">
        <View style={styles.row}>
          <Settings size={18} color={colors.textMuted} />
          <Text style={[typography.body, { color: colors.textMuted, marginLeft: spacing.sm, flex: 1 }]}>
            Organization settings are managed on the web console.
          </Text>
        </View>
      </Card>

      <View style={{ marginTop: spacing.xl }}>
        <Button
          title="Sign out"
          variant="ghost"
          icon={<LogOut size={16} color={colors.primary} />}
          onPress={() => void signOut()}
          fullWidth
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center" },
});
