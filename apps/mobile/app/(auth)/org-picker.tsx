import { useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "@/theme";
import { useAuth } from "@/lib/auth/AuthContext";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import type { MyOrganization } from "@/lib/api";

export default function OrgPickerScreen() {
  const { colors, typography, spacing, radius } = useTheme();
  const { orgChoices, pickOrganization, signOut } = useAuth();
  const insets = useSafeAreaInsets();
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function choose(org: MyOrganization) {
    setPendingId(org.id);
    setError(null);
    try {
      await pickOrganization(org.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not switch organization");
      setPendingId(null);
    }
  }

  return (
    <View
      style={[
        styles.flex,
        {
          backgroundColor: colors.background,
          paddingTop: insets.top + spacing.xl,
          paddingBottom: insets.bottom + spacing.md,
          paddingHorizontal: spacing.screen,
        },
      ]}
    >
      <Text style={[typography.display, { color: colors.primaryDark }]}>
        Choose a workspace
      </Text>
      <Text style={[typography.body, { color: colors.textMuted, marginTop: spacing.sm }]}>
        Your account belongs to more than one organization. Pick which one to use on this
        device.
      </Text>

      {error ? (
        <Text style={[typography.caption, { color: colors.error, marginTop: spacing.md }]}>
          {error}
        </Text>
      ) : null}

      <FlatList
        style={{ marginTop: spacing.lg }}
        data={orgChoices ?? []}
        keyExtractor={(item) => item.id}
        ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
        renderItem={({ item }) => (
          <Card onPress={() => void choose(item)}>
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={[typography.bodyMedium, { color: colors.text }]}>{item.name}</Text>
                <Text style={[typography.caption, { color: colors.textMuted, marginTop: 2 }]}>
                  {item.role_name ?? "Member"}
                  {item.is_primary ? " · Primary" : ""}
                </Text>
              </View>
              {pendingId === item.id ? (
                <View
                  style={[
                    styles.pill,
                    { backgroundColor: colors.primary, borderRadius: radius.sm },
                  ]}
                >
                  <Text style={[typography.caption, { color: colors.textInverse }]}>
                    Loading…
                  </Text>
                </View>
              ) : null}
            </View>
          </Card>
        )}
      />

      <Button
        title="Sign in with a different account"
        variant="ghost"
        onPress={() => void signOut()}
        style={{ marginTop: spacing.lg }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  row: { flexDirection: "row", alignItems: "center" },
  pill: { paddingVertical: 4, paddingHorizontal: 10 },
});
