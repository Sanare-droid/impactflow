import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useTheme } from "@/theme";
import { getBeneficiary, updateLocalBeneficiary } from "@/lib/db/repo";
import type { LocalBeneficiary } from "@/lib/db/types";
import { useSync } from "@/lib/sync/SyncContext";
import { Screen } from "@/components/ui/Screen";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function BeneficiaryDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors, typography, spacing } = useTheme();
  const { online, syncNow, refreshStatus } = useSync();
  const [item, setItem] = useState<LocalBeneficiary | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    void getBeneficiary(id).then((b) => {
      if (b) {
        setItem(b);
        setFirstName(b.first_name);
        setLastName(b.last_name);
        setPhone(b.phone ?? "");
      }
    });
  }, [id]);

  async function onSave() {
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      await updateLocalBeneficiary(id, {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone: phone.trim() || null,
      });
      await refreshStatus();
      if (online) void syncNow();
      router.back();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (!item) {
    return (
      <View style={{ padding: spacing.screen }}>
        <SkeletonCard />
      </View>
    );
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={[typography.heading, { color: colors.text }]}>
          {item.first_name} {item.last_name}
        </Text>
        {item.sync_status !== "synced" && (
          <Badge
            label={item.sync_status}
            variant={item.sync_status === "failed" ? "error" : "warning"}
          />
        )}
      </View>

      {item.code ? (
        <Text style={[typography.caption, { color: colors.textMuted, marginBottom: spacing.lg }]}>
          Code: {item.code}
        </Text>
      ) : null}

      <Card padding="md">
        <Input label="First name" value={firstName} onChangeText={setFirstName} />
        <View style={{ height: spacing.md }} />
        <Input label="Last name" value={lastName} onChangeText={setLastName} />
        <View style={{ height: spacing.md }} />
        <Input label="Phone" value={phone} onChangeText={setPhone} keyboardType="phone-pad" />
      </Card>

      {item.last_error ? (
        <Text style={[typography.caption, { color: colors.error, marginTop: spacing.md }]}>
          {item.last_error}
        </Text>
      ) : null}
      {error ? (
        <Text style={[typography.caption, { color: colors.error, marginTop: spacing.md }]}>{error}</Text>
      ) : null}

      <View style={{ marginTop: spacing.xl }}>
        <Button title="Save changes" onPress={() => void onSave()} loading={busy} fullWidth />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
});
