import { StyleSheet, Text, View } from "react-native";
import { useTheme } from "@/theme";
import { Button } from "./Button";

type Props = {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ icon, title, description, actionLabel, onAction }: Props) {
  const { colors, typography, spacing } = useTheme();

  return (
    <View style={[styles.wrap, { padding: spacing.xxl }]}>
      {icon ? <View style={{ marginBottom: spacing.lg }}>{icon}</View> : null}
      <Text style={[typography.title, { color: colors.text, textAlign: "center" }]}>{title}</Text>
      <Text
        style={[
          typography.body,
          { color: colors.textMuted, textAlign: "center", marginTop: spacing.sm },
        ]}
      >
        {description}
      </Text>
      {actionLabel && onAction ? (
        <View style={{ marginTop: spacing.lg, alignSelf: "stretch" }}>
          <Button title={actionLabel} onPress={onAction} fullWidth variant="secondary" />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center", justifyContent: "center" },
});
