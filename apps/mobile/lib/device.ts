import { Platform } from "react-native";
import Constants from "expo-constants";
import { getSetting, setSetting } from "@/lib/db/repo";
import { newLocalId } from "@/lib/id";

const DEVICE_KEY_SETTING = "device_key";
const DEVICE_ID_SETTING = "device_id";

export async function getOrCreateDeviceKey(): Promise<string> {
  const existing = await getSetting(DEVICE_KEY_SETTING);
  if (existing) return existing;
  const key = `if-${Platform.OS}-${newLocalId()}`;
  await setSetting(DEVICE_KEY_SETTING, key);
  return key;
}

export async function getDeviceId(): Promise<string | null> {
  return getSetting(DEVICE_ID_SETTING);
}

export async function setDeviceId(id: string): Promise<void> {
  await setSetting(DEVICE_ID_SETTING, id);
}

export function getDeviceName(): string {
  const model = Constants.deviceName ?? "Field Device";
  return model.slice(0, 255);
}

export function getAppVersion(): string {
  return Constants.expoConfig?.version ?? "1.0.0";
}

export function getPlatform(): string {
  return Platform.OS;
}
