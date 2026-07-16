import { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useFocusEffect, useLocalSearchParams } from "expo-router";
import { api, type SurveyField } from "@/lib/api";
import { createLocalSurveyResponse, getLocalSurvey, listLocalSurveyResponses } from "@/lib/db/repo";
import type { LocalSurvey, LocalSurveyResponse } from "@/lib/db/types";
import { flattenSurveyFields, normalizeFieldType, validateAnswers } from "@/lib/surveys";
import { useSync } from "@/lib/sync/SyncContext";

type AnswerMap = Record<string, unknown>;

function SyncBadge({ status }: { status: LocalSurveyResponse["sync_status"] }) {
  if (status === "synced") return null;
  return (
    <Text style={[styles.badge, status === "failed" ? styles.badgeFail : styles.badgePending]}>
      {status}
    </Text>
  );
}

export default function SurveyCaptureScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
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
      <View style={styles.container}>
        <Text style={styles.error}>{loadError}</Text>
      </View>
    );
  }

  if (!survey) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color="#0F766E" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>{survey.name}</Text>
      <Text style={styles.muted}>
        {survey.code || "—"} · v{survey.current_version} ·{" "}
        {online ? "online" : "offline — will sync later"}
      </Text>

      {fields.length === 0 ? (
        <Text style={styles.muted}>This survey has no capturable fields yet.</Text>
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

      {banner && <Text style={styles.banner}>{banner}</Text>}

      <View style={styles.actionsRow}>
        <Pressable
          style={[styles.button, styles.buttonSecondary]}
          onPress={() => void save("draft")}
          disabled={busy}
        >
          <Text style={styles.buttonSecondaryText}>Save draft</Text>
        </Pressable>
        <Pressable
          style={[styles.button, styles.buttonPrimary]}
          onPress={() => void save("submitted")}
          disabled={busy}
        >
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>{online ? "Submit" : "Submit offline"}</Text>
          )}
        </Pressable>
      </View>

      {responses.length > 0 && (
        <View style={styles.historySection}>
          <Text style={styles.historyTitle}>Saved on this device</Text>
          {responses.map((r) => (
            <View key={r.local_id} style={styles.historyRow}>
              <Text style={styles.historyText}>
                {r.status} · {new Date(r.updated_at_local).toLocaleString()}
              </Text>
              <SyncBadge status={r.sync_status} />
            </View>
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
      <View style={styles.field}>
        <Text style={styles.label}>{label}</Text>
        <View style={styles.chips}>
          {options.map((opt) => (
            <Pressable
              key={opt.value}
              style={[styles.chip, value === opt.value && styles.chipActive]}
              onPress={() => onChange(opt.value)}
            >
              <Text style={[styles.chipText, value === opt.value && styles.chipTextActive]}>
                {opt.label}
              </Text>
            </Pressable>
          ))}
        </View>
        {error && <Text style={styles.fieldError}>{error}</Text>}
      </View>
    );
  }

  if (type === "boolean") {
    return (
      <View style={styles.field}>
        <Text style={styles.label}>{label}</Text>
        <View style={styles.chips}>
          {[
            { value: true, text: "Yes" },
            { value: false, text: "No" },
          ].map((opt) => (
            <Pressable
              key={opt.text}
              style={[styles.chip, value === opt.value && styles.chipActive]}
              onPress={() => onChange(opt.value)}
            >
              <Text style={[styles.chipText, value === opt.value && styles.chipTextActive]}>
                {opt.text}
              </Text>
            </Pressable>
          ))}
        </View>
        {error && <Text style={styles.fieldError}>{error}</Text>}
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
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, type === "long_text" && styles.inputMultiline]}
        value={value === undefined || value === null ? "" : String(value)}
        onChangeText={onChange}
        keyboardType={keyboardType}
        multiline={type === "long_text"}
        numberOfLines={type === "long_text" ? 4 : 1}
        placeholder={type === "date" ? "YYYY-MM-DD" : undefined}
        autoCapitalize={type === "email" ? "none" : "sentences"}
      />
      {error && <Text style={styles.fieldError}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#FAFAF9" },
  content: { padding: 20, gap: 14, paddingBottom: 48 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  heading: { fontSize: 22, fontWeight: "700", color: "#134E4A" },
  muted: { color: "#78716C", fontSize: 13 },
  field: { gap: 6 },
  label: { fontWeight: "600", color: "#1C1917", fontSize: 14 },
  input: {
    borderWidth: 1,
    borderColor: "#E7E5E4",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: "#fff",
  },
  inputMultiline: { minHeight: 90, textAlignVertical: "top" },
  fieldError: { color: "#E11D48", fontSize: 12 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: "#E7E5E4",
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: "#fff",
  },
  chipActive: { backgroundColor: "#0F766E", borderColor: "#0F766E" },
  chipText: { color: "#44403C", fontSize: 13 },
  chipTextActive: { color: "#fff", fontWeight: "600" },
  banner: {
    backgroundColor: "#FEF3C7",
    color: "#92400E",
    borderRadius: 10,
    padding: 10,
    fontSize: 13,
  },
  actionsRow: { flexDirection: "row", gap: 10, marginTop: 8 },
  button: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  buttonPrimary: { backgroundColor: "#0F766E" },
  buttonSecondary: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#0F766E" },
  buttonText: { color: "#fff", fontWeight: "600" },
  buttonSecondaryText: { color: "#0F766E", fontWeight: "600" },
  error: { color: "#E11D48", padding: 20 },
  historySection: { marginTop: 12, gap: 8 },
  historyTitle: { fontWeight: "600", color: "#1C1917" },
  historyRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#F5F5F4",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  historyText: { color: "#44403C", fontSize: 13 },
  badge: {
    fontSize: 10,
    fontWeight: "700",
    textTransform: "uppercase",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    overflow: "hidden",
  },
  badgePending: { backgroundColor: "#FEF3C7", color: "#92400E" },
  badgeFail: { backgroundColor: "#FFE4E6", color: "#9F1239" },
});
