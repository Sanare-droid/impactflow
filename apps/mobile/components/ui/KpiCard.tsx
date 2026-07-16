import { StyleSheet, Text, View } from "react-native";
import { useTheme } from "@/theme";
import { Card } from "./Card";

type Props = {
  label: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  icon?: React.ReactNode;
};

export function KpiCard({ label, value, subtitle, trend, icon }: Props) {
  const { colors, typography, spacing } = useTheme();

  const trendColor =
    trend === "up" ? colors.success : trend === "down" ? colors.error : colors.textMuted;

  return (
    <Card padding="md" style={styles.card}>
      <View style={styles.row}>
        <Text style={[typography.label, { color: colors.textMuted }]}>{label}</Text>
        {icon}
      </View>
      <Text style={[typography.heading, { color: colors.text, marginTop: spacing.xs }]}>
        {value}
      </Text>
      {subtitle ? (
        <Text style={[typography.caption, { color: trendColor, marginTop: spacing.xs }]}>
          {subtitle}
        </Text>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { flex: 1, minWidth: 140 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
});
