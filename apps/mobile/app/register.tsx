import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useTheme } from "@/theme";
import { api } from "@/lib/api";
import { createLocalBeneficiary } from "@/lib/db/repo";
import { useSync } from "@/lib/sync/SyncContext";
import { Screen } from "@/components/ui/Screen";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function RegisterScreen() {
  const { colors, typography, spacing } = useTheme();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { online, syncNow, refreshStatus } = useSync();

  async function onSubmit() {
    setBusy(true);
    setError(null);
    try {
      await createLocalBeneficiary({
        organization_id: api.organizationId,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone: phone.trim() || undefined,
      });
      await refreshStatus();
      if (online) void syncNow();
      router.back();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Card padding="md" style={{ marginBottom: spacing.lg }}>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          {online
            ? "Saved locally and synced via batch sync when the API is reachable."
            : "You are offline — this registration will sync when you reconnect."}
        </Text>
      </Card>

      <Input label="First name" placeholder="First name" value={firstName} onChangeText={setFirstName} />
      <View style={{ height: spacing.md }} />
      <Input label="Last name" placeholder="Last name" value={lastName} onChangeText={setLastName} />
      <View style={{ height: spacing.md }} />
      <Input
        label="Phone"
        placeholder="Phone number"
        keyboardType="phone-pad"
        value={phone}
        onChangeText={setPhone}
      />

      {error ? (
        <Text style={[typography.caption, { color: colors.error, marginTop: spacing.md }]}>{error}</Text>
      ) : null}

      <View style={{ marginTop: spacing.xl }}>
        <Button
          title={online ? "Save beneficiary" : "Save offline"}
          onPress={() => void onSubmit()}
          loading={busy}
          disabled={!firstName.trim() || !lastName.trim()}
          fullWidth
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({});
