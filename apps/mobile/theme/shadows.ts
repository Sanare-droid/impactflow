import { Platform, ViewStyle } from "react-native";

export type ShadowStyle = Pick<ViewStyle, "shadowColor" | "shadowOffset" | "shadowOpacity" | "shadowRadius" | "elevation">;

export type ShadowScale = {
  sm: ShadowStyle;
  md: ShadowStyle;
  lg: ShadowStyle;
};

const base = Platform.select({
  ios: {
    shadowColor: "#1C1917",
    shadowOffset: { width: 0, height: 2 },
  },
  android: {
    elevation: 2,
  },
  default: {},
}) as ShadowStyle;

export const shadows: ShadowScale = {
  sm: {
    ...base,
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  md: {
    ...base,
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  lg: {
    ...base,
    shadowOpacity: 0.14,
    shadowRadius: 16,
    elevation: 8,
  },
};
