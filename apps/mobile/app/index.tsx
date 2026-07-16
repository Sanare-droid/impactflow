import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Link, useFocusEffect } from "expo-router";
import { api } from "@/lib/api";
import { getDb } from "@/lib/db";
import { listLocalBeneficiaries } from "@/lib/db/repo";
import type { LocalBeneficiary } from "@/lib/db/types";
import { clearSession, hydrateSession, persistSession } from "@/lib/session";
import { useSync } from "@/lib/sync/SyncContext";
import { SyncBanner } from "@/components/SyncBanner";

export default function HomeScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authed, setAuthed] = useState(false);
  const [items, setItems] = useState<LocalBeneficiary[]>([]);
  const { online, syncNow, refreshStatus } = useSync();

  const hydrate = useCallback(async () => {
    try {
      await getDb();
    } catch {
      /* ignore on unsupported platforms */
    }
    const ok = await hydrateSession();
    setAuthed(ok);
  }, []);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  const loadBeneficiaries = useCallback(async () => {
    if (!api.accessToken) return;
    try {
      const local = await listLocalBeneficiaries();
      setItems(local);
      setError(null);
      if (online) {
        await syncNow();
        const refreshed = await listLocalBeneficiaries();
        setItems(refreshed);
      }
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      try {
        setItems(await listLocalBeneficiaries());
      } catch {
        /* empty */
      }
    }
  }, [online, refreshStatus, syncNow]);

  useFocusEffect(
    useCallback(() => {
      void loadBeneficiaries();
    }, [loadBeneficiaries]),
  );

  async function onLogin() {
    setBusy(true);
    setError(null);
    try {
      const tokens = await api.login(email.trim(), password);
      if (tokens.mfa_required) {
        throw new Error("MFA required — complete setup on web first");
      }
      const orgId = tokens.user?.primary_organization_id ?? null;
      await persistSession({
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        organization_id: orgId,
      });
      setAuthed(true);
      await loadBeneficiaries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function onLogout() {
    await clearSession();
    setAuthed(false);
    setItems([]);
  }

  if (!authed) {
    return (
      <View style={styles.container}>
        <Text style={styles.brand}>ImpactFlow Field</Text>
        <Text style={styles.subtitle}>Offline-ready beneficiary registration</Text>
        <TextInput
          style={styles.input}
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="Email"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          secureTextEntry
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
        />
        {error && <Text style={styles.error}>{error}</Text>}
        <Pressable style={styles.button} onPress={onLogin} disabled={busy}>
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Sign in</Text>
          )}
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <Text style={styles.heading}>Caseload</Text>
        <Pressable onPress={onLogout}>
          <Text style={styles.link}>Sign out</Text>
        </Pressable>
      </View>
      <SyncBanner />
      {error && <Text style={styles.error}>{error}</Text>}
      <Link href="/register" asChild>
        <Pressable style={styles.button}>
          <Text style={styles.buttonText}>Register beneficiary</Text>
        </Pressable>
      </Link>
      <FlatList
        style={{ marginTop: 16 }}
        data={items}
        keyExtractor={(item) => item.local_id}
        ListEmptyComponent={<Text style={styles.muted}>No beneficiaries yet.</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.cardTitle}>
                {item.first_name} {item.last_name}
              </Text>
              {item.sync_status !== "synced" && (
                <Text
                  style={[
                    styles.badge,
                    item.sync_status === "failed" ? styles.badgeFail : styles.badgePending,
                  ]}
                >
                  {item.sync_status}
                </Text>
              )}
            </View>
            <Text style={styles.muted}>
              {item.code || "local"} · {item.phone || "no phone"} · {item.status}
            </Text>
            {item.last_error ? (
              <Text style={styles.errorSmall}>{item.last_error}</Text>
            ) : null}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, gap: 12 },
  brand: { fontSize: 28, fontWeight: "700", color: "#134E4A", marginTop: 24 },
  subtitle: { color: "#78716C", marginBottom: 12 },
  heading: { fontSize: 22, fontWeight: "600", color: "#1C1917" },
  input: {
    borderWidth: 1,
    borderColor: "#E7E5E4",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: "#fff",
  },
  button: {
    backgroundColor: "#0F766E",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  buttonText: { color: "#fff", fontWeight: "600" },
  error: { color: "#E11D48" },
  errorSmall: { color: "#E11D48", fontSize: 11, marginTop: 4 },
  muted: { color: "#78716C", fontSize: 13 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  link: { color: "#0F766E", fontWeight: "600" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#F5F5F4",
  },
  cardTitle: { fontWeight: "600", color: "#1C1917", marginBottom: 4, flex: 1 },
  badge: {
    fontSize: 10,
    fontWeight: "700",
    textTransform: "uppercase",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    overflow: "hidden",
  },
  badgePending: { backgroundColor: "#FEF3C7", color: "#92400E" },
  badgeFail: { backgroundColor: "#FFE4E6", color: "#9F1239" },
});
