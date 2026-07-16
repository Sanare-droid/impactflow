import { TextStyle } from "react-native";

export type FontFamily = {
  regular: string;
  medium: string;
  semiBold: string;
  bold: string;
};

export const fontFamily: FontFamily = {
  regular: "Manrope_400Regular",
  medium: "Manrope_500Medium",
  semiBold: "Manrope_600SemiBold",
  bold: "Manrope_700Bold",
};

export type TypographyScale = {
  display: TextStyle;
  heading: TextStyle;
  title: TextStyle;
  body: TextStyle;
  bodyMedium: TextStyle;
  caption: TextStyle;
  label: TextStyle;
};

export const typography: TypographyScale = {
  display: {
    fontFamily: fontFamily.bold,
    fontSize: 32,
    lineHeight: 40,
    letterSpacing: -0.5,
  },
  heading: {
    fontFamily: fontFamily.bold,
    fontSize: 24,
    lineHeight: 32,
    letterSpacing: -0.3,
  },
  title: {
    fontFamily: fontFamily.semiBold,
    fontSize: 18,
    lineHeight: 26,
  },
  body: {
    fontFamily: fontFamily.regular,
    fontSize: 15,
    lineHeight: 22,
  },
  bodyMedium: {
    fontFamily: fontFamily.medium,
    fontSize: 15,
    lineHeight: 22,
  },
  caption: {
    fontFamily: fontFamily.regular,
    fontSize: 13,
    lineHeight: 18,
  },
  label: {
    fontFamily: fontFamily.semiBold,
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.3,
    textTransform: "uppercase",
  },
};
