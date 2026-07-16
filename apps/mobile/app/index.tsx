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
import * as SecureStore from "expo-secure-store";
import { api, Beneficiary } from "@/lib/api";

const ACCESS_KEY = "if_access_token";
const REFRESH_KEY = "if_refresh_token";
const ORG_KEY = "if_organization_id";

export default function HomeScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authed, setAuthed] = useState(false);
  const [items, setItems] = useState<Beneficiary[]>([]);

  const hydrate = useCallback(async () => {
    const access = await SecureStore.getItemAsync(ACCESS_KEY);
    const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
    const org = await SecureStore.getItemAsync(ORG_KEY);
    if (access && refresh) {
      api.setSession({
        access_token: access,
        refresh_token: refresh,
        organization_id: org,
      });
      setAuthed(true);
    }
  }, []);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  const loadBeneficiaries = useCallback(async () => {
    if (!api.accessToken) return;
    try {
      const data = await api.listBeneficiaries();
      setItems(data.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, []);

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
      api.setSession({
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        organization_id: orgId,
      });
      await SecureStore.setItemAsync(ACCESS_KEY, tokens.access_token);
      await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh_token);
      if (orgId) {
        await SecureStore.setItemAsync(ORG_KEY, orgId);
      }
      setAuthed(true);
      await loadBeneficiaries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function onLogout() {
    api.clearSession();
    await SecureStore.deleteItemAsync(ACCESS_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
    await SecureStore.deleteItemAsync(ORG_KEY);
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
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Sign in</Text>}
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
      {error && <Text style={styles.error}>{error}</Text>}
      <Link href="/register" asChild>
        <Pressable style={styles.button}>
          <Text style={styles.buttonText}>Register beneficiary</Text>
        </Pressable>
      </Link>
      <FlatList
        style={{ marginTop: 16 }}
        data={items}
        keyExtractor={(item) => item.id}
        ListEmptyComponent={<Text style={styles.muted}>No beneficiaries yet.</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>
              {item.first_name} {item.last_name}
            </Text>
            <Text style={styles.muted}>
              {item.code} · {item.phone || "no phone"} · {item.status}
            </Text>
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
  cardTitle: { fontWeight: "600", color: "#1C1917", marginBottom: 4 },
});
