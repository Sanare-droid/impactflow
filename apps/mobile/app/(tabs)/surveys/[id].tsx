import { useCallback, useMemo, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { useFocusEffect, useLocalSearchParams } from "expo-router";
import type { SurveyField } from "@/lib/api";
import { createLocalSurveyResponse, getLocalSurvey, listLocalSurveyResponses } from "@/lib/db/repo";
import type { LocalSurvey, LocalSurveyResponse } from "@/lib/db/types";
import { flattenSurveyFields, normalizeFieldType, validateAnswers } from "@/lib/surveys";
import { useSync } from "@/lib/sync/SyncContext";
import { useTheme } from "@/theme";
import { Input } from "@/components/ui/Input";
import { Chip } from "@/components/ui/Chip";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

type AnswerMap = Record<string, unknown>;

export default function SurveyCaptureScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors, typography, spacing } = useTheme();
  const [survey, setSurvey] = useState<LocalSurvey | null>(null);
  const [responses, setResponses] = useState<LocalSurveyResponse[]>([]);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { online, syncNow, refreshStatus } = useSync();

  const fields: SurveyField[] = useMemo(() => {
    if (!survey) return [];
    try {
      return flattenSurveyFields(JSON.parse(survey.schema_json));
    } catch {
      return [];
    }
  }, [survey]);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const local = await getLocalSurvey(id);
      setSurvey(local);
      setResponses(await listLocalSurveyResponses(id));
      setLoadError(local ? null : "Survey not found offline. Sync while online first.");
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load survey");
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  function setAnswer(fieldId: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
    setErrors((prev) => {
      if (!(fieldId in prev)) return prev;
      const next = { ...prev };
      delete next[fieldId];
      return next;
    });
  }

  async function save(status: "draft" | "submitted") {
    if (!survey) return;
    setBanner(null);
    if (status === "submitted") {
      const validation = validateAnswers(fields, answers);
      if (Object.keys(validation).length > 0) {
        setErrors(validation);
        setBanner("Fix the highlighted fields before submitting.");
        return;
      }
    }
    setBusy(true);
    try {
      await createLocalSurveyResponse({
        survey_local_id: survey.local_id,
        survey_server_id: survey.server_id,
        organization_id: survey.organization_id,
        status,
        answers,
      });
      if (status === "submitted") {
        await refreshStatus();
        if (online) void syncNow();
        setAnswers({});
        setErrors({});
        setBanner("Response submitted — it will sync automatically when online.");
      } else {
        setBanner("Draft saved on this device.");
      }
      setResponses(await listLocalSurveyResponses(survey.local_id));
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Failed to save response");
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <View style={[styles.centered, { backgroundColor: colors.background }]}>
        <Text style={[typography.body, { color: colors.error }]}>{loadError}</Text>
      </View>
    );
  }

  if (!survey) {
    return (
      <View style={[styles.centered, { backgroundColor: colors.background }]}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={{ padding: spacing.screen, gap: spacing.md, paddingBottom: 48 }}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={[typography.heading, { color: colors.primaryDark }]}>{survey.name}</Text>
      <Text style={[typography.caption, { color: colors.textMuted }]}>
        {survey.code || "—"} · v{survey.current_version} · {online ? "online" : "offline"}
      </Text>

      {fields.length === 0 ? (
        <Text style={[typography.body, { color: colors.textMuted }]}>
          This survey has no capturable fields yet.
        </Text>
      ) : (
        fields.map((field) => (
          <FieldInput
            key={field.id}
            field={field}
            value={answers[field.id]}
            error={errors[field.id]}
            onChange={(value) => setAnswer(field.id, value)}
          />
        ))
      )}

      {banner && (
        <Card padding="md">
          <Text style={[typography.caption, { color: colors.warning }]}>{banner}</Text>
        </Card>
      )}

      <View style={styles.actionsRow}>
        <Button title="Save draft" variant="secondary" onPress={() => void save("draft")} disabled={busy} />
        <Button
          title={online ? "Submit" : "Submit offline"}
          onPress={() => void save("submitted")}
          loading={busy}
        />
      </View>

      {responses.length > 0 && (
        <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
          <Text style={[typography.title, { color: colors.text }]}>Saved on this device</Text>
          {responses.map((r) => (
            <Card key={r.local_id} padding="md">
              <View style={styles.historyRow}>
                <Text style={[typography.caption, { color: colors.textSecondary }]}>
                  {r.status} · {new Date(r.updated_at_local).toLocaleString()}
                </Text>
                {r.sync_status !== "synced" && (
                  <Badge
                    label={r.sync_status}
                    variant={r.sync_status === "failed" ? "error" : "warning"}
                  />
                )}
              </View>
            </Card>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function FieldInput({
  field,
  value,
  error,
  onChange,
}: {
  field: SurveyField;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
}) {
  const type = normalizeFieldType(field.type);
  const label = `${field.label}${field.required ? " *" : ""}`;

  if (type === "dropdown" || type === "radio") {
    const options = field.options ?? [];
    return (
      <View style={{ gap: 8 }}>
        <Text style={{ fontFamily: "Manrope_600SemiBold", fontSize: 14 }}>{label}</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {options.map((opt) => (
            <Chip
              key={opt.value}
              label={opt.label}
              selected={value === opt.value}
              onPress={() => onChange(opt.value)}
            />
          ))}
        </View>
        {error && <Text style={{ color: "#E11D48", fontSize: 12 }}>{error}</Text>}
      </View>
    );
  }

  if (type === "boolean") {
    return (
      <View style={{ gap: 8 }}>
        <Text style={{ fontFamily: "Manrope_600SemiBold", fontSize: 14 }}>{label}</Text>
        <View style={{ flexDirection: "row", gap: 8 }}>
          <Chip label="Yes" selected={value === true} onPress={() => onChange(true)} />
          <Chip label="No" selected={value === false} onPress={() => onChange(false)} />
        </View>
        {error && <Text style={{ color: "#E11D48", fontSize: 12 }}>{error}</Text>}
      </View>
    );
  }

  const keyboardType =
    type === "number"
      ? "numeric"
      : type === "email"
        ? "email-address"
        : type === "phone"
          ? "phone-pad"
          : "default";

  return (
    <Input
      label={label}
      value={value === undefined || value === null ? "" : String(value)}
      onChangeText={onChange}
      keyboardType={keyboardType}
      multiline={type === "long_text"}
      numberOfLines={type === "long_text" ? 4 : 1}
      placeholder={type === "date" ? "YYYY-MM-DD" : undefined}
      autoCapitalize={type === "email" ? "none" : "sentences"}
      error={error}
    />
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  actionsRow: { flexDirection: "row", gap: 10, marginTop: 8 },
  historyRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
});
