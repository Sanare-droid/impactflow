import { ScrollView, StyleSheet, View, type ScrollViewProps } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "@/theme";

type Props = ScrollViewProps & {
  padded?: boolean;
  safeTop?: boolean;
  children: React.ReactNode;
};

export function Screen({
  children,
  padded = true,
  safeTop = false,
  contentContainerStyle,
  style,
  ...rest
}: Props) {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      {...rest}
      style={[styles.screen, { backgroundColor: colors.background }, style]}
      contentContainerStyle={[
        {
          paddingTop: safeTop ? insets.top + spacing.md : spacing.md,
          paddingBottom: insets.bottom + spacing.xxl,
          paddingHorizontal: padded ? spacing.screen : 0,
        },
        contentContainerStyle,
      ]}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  );
}

export function ScreenBody({ children }: { children: React.ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.body, { backgroundColor: colors.background, flex: 1 }]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  body: { flex: 1 },
});
