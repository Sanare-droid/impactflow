import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

export default function RootLayout() {
  return (
    <>
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
    </>
  );
}
