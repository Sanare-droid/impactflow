import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SyncProvider } from "@/lib/sync/SyncContext";

export default function RootLayout() {
  return (
    <SyncProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: "#F0FDFA" },
          headerTintColor: "#134E4A",
          headerTitleStyle: { fontWeight: "600" },
          contentStyle: { backgroundColor: "#FAFAF9" },
        }}
      >
        <Stack.Screen name="index" options={{ title: "ImpactFlow Field" }} />
        <Stack.Screen name="register" options={{ title: "Register beneficiary" }} />
      </Stack>
    </SyncProvider>
  );
}
