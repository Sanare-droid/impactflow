import * as SecureStore from "expo-secure-store";
import { api } from "@/lib/api";
import { ACCESS_KEY, ORG_KEY, REFRESH_KEY, USER_KEY } from "@/lib/sessionKeys";

export { ACCESS_KEY, ORG_KEY, REFRESH_KEY, USER_KEY } from "@/lib/sessionKeys";

export async function hydrateSession(): Promise<boolean> {
  const access = await SecureStore.getItemAsync(ACCESS_KEY);
  const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
  const org = await SecureStore.getItemAsync(ORG_KEY);
  const userId = await SecureStore.getItemAsync(USER_KEY);
  if (!access || !refresh) return false;
  api.setSession({
    access_token: access,
    refresh_token: refresh,
    organization_id: org,
    user_id: userId,
  });
  return true;
}

export async function persistSession(tokens: {
  access_token: string;
  refresh_token: string;
  organization_id?: string | null;
  user_id?: string | null;
}) {
  api.setSession(tokens);
  await SecureStore.setItemAsync(ACCESS_KEY, tokens.access_token);
  await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh_token);
  if (tokens.organization_id) {
    await SecureStore.setItemAsync(ORG_KEY, tokens.organization_id);
  }
  if (tokens.user_id) {
    await SecureStore.setItemAsync(USER_KEY, tokens.user_id);
  }
}

export async function clearSession() {
  api.clearSession();
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
  await SecureStore.deleteItemAsync(ORG_KEY);
  await SecureStore.deleteItemAsync(USER_KEY);
}
