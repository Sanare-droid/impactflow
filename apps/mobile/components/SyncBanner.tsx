import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Cloud, CloudOff, RefreshCw, AlertTriangle } from "lucide-react-native";
import { useTheme } from "@/theme";
import { useSync } from "@/lib/sync/SyncContext";

function formatWhen(iso: string | null): string {
  if (!iso) return "Never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

type Props = {
  compact?: boolean;
};

export function SyncBanner({ compact = false }: Props) {
  const { colors, typography, spacing, radius } = useTheme();
  const { online, syncing, pending, failed, lastSyncAt, error, syncNow, retryFailed } = useSync();

  const bg = failed > 0 ? colors.errorMuted : online ? colors.primaryMuted : colors.warningMuted;
  const accent = failed > 0 ? colors.error : online ? colors.primaryDark : colors.warning;

  return (
    <View
      style={[
        styles.banner,
        {
          backgroundColor: bg,
          borderRadius: radius.md,
          padding: compact ? spacing.sm : spacing.md,
          marginBottom: spacing.sm,
        },
      ]}
    >
      <View style={styles.iconWrap}>
        {failed > 0 ? (
          <AlertTriangle size={18} color={accent} />
        ) : online ? (
          <Cloud size={18} color={accent} />
        ) : (
          <CloudOff size={18} color={accent} />
        )}
      </View>
      <View style={styles.copy}>
        <Text style={[typography.bodyMedium, { color: accent, fontSize: compact ? 13 : 14 }]}>
          {online ? "Online" : "Offline"}
          {pending > 0 ? ` · ${pending} pending` : " · queue clear"}
          {failed > 0 ? ` · ${failed} failed` : ""}
        </Text>
        {!compact && (
          <Text style={[typography.caption, { color: colors.textSecondary, marginTop: 2 }]}>
            Last sync: {formatWhen(lastSyncAt)}
          </Text>
        )}
        {error ? (
          <Text style={[typography.caption, { color: colors.error, marginTop: 2 }]}>{error}</Text>
        ) : null}
      </View>
      <View style={styles.actions}>
        {failed > 0 ? (
          <Pressable onPress={() => void retryFailed()} disabled={syncing}>
            <Text style={[typography.caption, { color: accent, fontFamily: typography.bodyMedium.fontFamily }]}>
              Retry
            </Text>
          </Pressable>
        ) : null}
        <Pressable
          onPress={() => void syncNow()}
          disabled={syncing || !online}
          style={{ opacity: syncing || !online ? 0.5 : 1 }}
        >
          {syncing ? (
            <ActivityIndicator color={accent} size="small" />
          ) : (
            <RefreshCw size={16} color={accent} />
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { flexDirection: "row", alignItems: "center", gap: 10 },
  iconWrap: { width: 24, alignItems: "center" },
  copy: { flex: 1 },
  actions: { flexDirection: "row", alignItems: "center", gap: 12 },
});
