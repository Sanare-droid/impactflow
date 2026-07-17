import { useEffect } from "react";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useFonts, Manrope_400Regular, Manrope_500Medium, Manrope_600SemiBold, Manrope_700Bold } from "@expo-google-fonts/manrope";
import { ThemeProvider, useTheme } from "@/theme";
import { AuthProvider, useAuth } from "@/lib/auth/AuthContext";
import { SyncProvider } from "@/lib/sync/SyncContext";

function RootNavigator() {
  const { authed, ready, orgChoices } = useAuth();
  const segments = useSegments();
  const router = useRouter();
  const { colors, isDark } = useTheme();

  useEffect(() => {
    if (!ready) return;
    const inAuth = segments[0] === "(auth)";
    if (!authed && orgChoices) {
      router.replace("/org-picker");
    } else if (!authed) {
      // Always resolve to /login when signed out, even from org-picker
      // (e.g. after "sign in with a different account" clears the pending choice).
      router.replace("/login");
    } else if (authed && inAuth) {
      router.replace("/(tabs)");
    }
  }, [authed, ready, orgChoices, segments, router]);

  return (
    <>
      <StatusBar style={isDark ? "light" : "dark"} />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.primaryDark,
          headerTitleStyle: { fontFamily: "Manrope_600SemiBold" },
          headerShadowVisible: false,
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="register" options={{ title: "Register beneficiary", presentation: "modal" }} />
        <Stack.Screen name="beneficiary/[id]" options={{ title: "Beneficiary" }} />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Manrope_400Regular,
    Manrope_500Medium,
    Manrope_600SemiBold,
    Manrope_700Bold,
  });

  if (!fontsLoaded) return null;

  return (
    <ThemeProvider>
      <AuthProvider>
        <SyncProvider>
          <RootNavigator />
        </SyncProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
