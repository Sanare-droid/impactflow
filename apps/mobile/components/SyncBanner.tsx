import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { useSync } from "@/lib/sync/SyncContext";

function formatWhen(iso: string | null): string {
  if (!iso) return "Never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function SyncBanner() {
  const {
    online,
    syncing,
    pending,
    failed,
    lastSyncAt,
    error,
    syncNow,
    retryFailed,
  } = useSync();

  return (
    <View
      style={[
        styles.banner,
        online ? styles.online : styles.offline,
        failed > 0 && styles.warn,
      ]}
    >
      <View style={styles.copy}>
        <Text style={styles.title}>
          {online ? "Online" : "Offline"} ·{" "}
          {pending > 0 ? `${pending} pending` : "queue clear"}
          {failed > 0 ? ` · ${failed} failed` : ""}
        </Text>
        <Text style={styles.meta}>Last sync: {formatWhen(lastSyncAt)}</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </View>
      <View style={styles.actions}>
        {failed > 0 ? (
          <Pressable style={styles.btn} onPress={() => void retryFailed()} disabled={syncing}>
            <Text style={styles.btnText}>Retry</Text>
          </Pressable>
        ) : null}
        <Pressable
          style={[styles.btn, !online && styles.btnDisabled]}
          onPress={() => void syncNow()}
          disabled={syncing || !online}
        >
          {syncing ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.btnText}>Sync</Text>
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    marginHorizontal: 20,
    marginTop: 8,
    marginBottom: 4,
    borderRadius: 12,
    padding: 12,
    flexDirection: "row",
    gap: 10,
    alignItems: "center",
  },
  online: { backgroundColor: "#CCFBF1" },
  offline: { backgroundColor: "#FEF3C7" },
  warn: { backgroundColor: "#FFE4E6" },
  copy: { flex: 1, gap: 2 },
  title: { fontWeight: "600", color: "#134E4A", fontSize: 13 },
  meta: { color: "#57534E", fontSize: 12 },
  error: { color: "#BE123C", fontSize: 12 },
  actions: { flexDirection: "row", gap: 6 },
  btn: {
    backgroundColor: "#0F766E",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    minWidth: 52,
    alignItems: "center",
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: "#fff", fontWeight: "600", fontSize: 12 },
});
