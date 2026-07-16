import { StyleSheet, Text, View } from "react-native";
import { useTheme } from "@/theme";

type BadgeVariant = "default" | "success" | "warning" | "error" | "info";

type Props = {
  label: string;
  variant?: BadgeVariant;
};

export function Badge({ label, variant = "default" }: Props) {
  const { colors, typography, radius, spacing } = useTheme();

  const variants: Record<BadgeVariant, { bg: string; text: string }> = {
    default: { bg: colors.backgroundSecondary, text: colors.textSecondary },
    success: { bg: colors.successMuted, text: colors.success },
    warning: { bg: colors.warningMuted, text: colors.warning },
    error: { bg: colors.errorMuted, text: colors.error },
    info: { bg: colors.infoMuted, text: colors.info },
  };

  const v = variants[variant];

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: v.bg,
          borderRadius: radius.sm,
          paddingHorizontal: spacing.sm,
          paddingVertical: 3,
        },
      ]}
    >
      <Text style={[typography.label, { color: v.text, fontSize: 10 }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { alignSelf: "flex-start" },
});
