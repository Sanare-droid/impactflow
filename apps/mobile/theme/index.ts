import {
  createContext,
  createElement,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useColorScheme } from "react-native";
import { darkColors, lightColors, type ColorPalette } from "./colors";
import { fontFamily, typography, type TypographyScale } from "./typography";
import { spacing, type Spacing } from "./spacing";
import { radius, type Radius } from "./radius";
import { shadows, type ShadowScale } from "./shadows";

export type Theme = {
  colors: ColorPalette;
  typography: TypographyScale;
  spacing: Spacing;
  radius: Radius;
  shadows: ShadowScale;
  fontFamily: typeof fontFamily;
  isDark: boolean;
};

const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const scheme = useColorScheme();
  const isDark = scheme === "dark";

  const theme = useMemo<Theme>(
    () => ({
      colors: isDark ? darkColors : lightColors,
      typography,
      spacing,
      radius,
      shadows,
      fontFamily,
      isDark,
    }),
    [isDark],
  );

  return createElement(ThemeContext.Provider, { value: theme }, children);
}

export function useTheme(): Theme {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    return {
      colors: lightColors,
      typography,
      spacing,
      radius,
      shadows,
      fontFamily,
      isDark: false,
    };
  }
  return ctx;
}

export { lightColors, darkColors, typography, spacing, radius, shadows, fontFamily };
