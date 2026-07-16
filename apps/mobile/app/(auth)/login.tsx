import { useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "@/theme";
import { useAuth } from "@/lib/auth/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function LoginScreen() {
  const { colors, typography, spacing, radius, shadows } = useTheme();
  const { signIn } = useAuth();
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onLogin() {
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: colors.background, paddingTop: insets.top }]}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={[styles.hero, { paddingHorizontal: spacing.screen }]}>
        <View style={[styles.logoMark, { backgroundColor: colors.primaryMuted, borderRadius: radius.lg }]}>
          <Text style={[typography.display, { color: colors.primaryDark, fontSize: 28 }]}>IF</Text>
        </View>
        <Text style={[typography.display, { color: colors.primaryDark, marginTop: spacing.lg }]}>
          ImpactFlow Field
        </Text>
        <Text style={[typography.body, { color: colors.textMuted, marginTop: spacing.sm }]}>
          Enterprise field operations — collect data offline, sync when connected.
        </Text>
      </View>

      <View
        style={[
          styles.card,
          {
            backgroundColor: colors.surface,
            marginHorizontal: spacing.screen,
            borderRadius: radius.xl,
            padding: spacing.xl,
            ...shadows.md,
          },
        ]}
      >
        <Text style={[typography.title, { color: colors.text, marginBottom: spacing.lg }]}>
          Sign in to continue
        </Text>
        <Input
          label="Work email"
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="you@organization.org"
          value={email}
          onChangeText={setEmail}
        />
        <View style={{ height: spacing.md }} />
        <Input
          label="Password"
          secureTextEntry
          placeholder="••••••••"
          value={password}
          onChangeText={setPassword}
        />
        {error ? (
          <Text style={[typography.caption, { color: colors.error, marginTop: spacing.md }]}>
            {error}
          </Text>
        ) : null}
        <View style={{ marginTop: spacing.lg }}>
          <Button
            title="Sign in"
            onPress={() => void onLogin()}
            loading={busy}
            fullWidth
            disabled={!email.trim() || !password}
          />
        </View>
      </View>

      <Text
        style={[
          typography.caption,
          { color: colors.textMuted, textAlign: "center", marginTop: spacing.xl, paddingHorizontal: spacing.screen },
        ]}
      >
        Your organization admin can invite you from the web console. Data syncs securely when online.
      </Text>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  hero: { paddingTop: 48, paddingBottom: 32 },
  logoMark: {
    width: 64,
    height: 64,
    alignItems: "center",
    justifyContent: "center",
  },
  card: {},
});
