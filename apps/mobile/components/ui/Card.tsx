import { Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";
import { useTheme } from "@/theme";

type Props = {
  children: React.ReactNode;
  onPress?: () => void;
  elevated?: boolean;
  padding?: "sm" | "md" | "lg";
  style?: StyleProp<ViewStyle>;
};

export function Card({ children, onPress, elevated = true, padding = "md", style }: Props) {
  const { colors, radius, shadows, spacing } = useTheme();

  const pad = padding === "sm" ? spacing.sm : padding === "lg" ? spacing.lg : spacing.md;

  const content = (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.surface,
          borderRadius: radius.lg,
          borderColor: colors.borderLight,
          padding: pad,
        },
        elevated && shadows.sm,
        style,
      ]}
    >
      {children}
    </View>
  );

  if (onPress) {
    return (
      <Pressable onPress={onPress} style={({ pressed }) => [{ opacity: pressed ? 0.92 : 1 }]}>
        {content}
      </Pressable>
    );
  }
  return content;
}

const styles = StyleSheet.create({
  card: { borderWidth: 1 },
});
