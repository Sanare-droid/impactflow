import { useCallback, useMemo, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { useFocusEffect, useLocalSearchParams } from "expo-router";
import { api, type SurveyField } from "@/lib/api";
import {
  createLocalSurveyResponse,
  enqueueMediaUpload,
  getLocalSurvey,
  listLocalSurveyResponses,
} from "@/lib/db/repo";
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
      const pendingField = fields.find((f) => {
        const v = answers[f.id];
        return typeof v === "object" && v !== null && (v as Record<string, unknown>).pending_upload === true;
      });
      if (pendingField) {
        setBanner(
          `"${pendingField.label}" is still waiting to upload. Connect to the internet and tap "Retry upload" before submitting.`,
        );
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

  if (type === "image" || type === "photo") {
    return (
      <MediaField
        label={label}
        value={value}
        error={error}
        onChange={onChange}
        mediaTypes="images"
      />
    );
  }

  if (type === "gps" || type === "location") {
    return <GpsField label={label} value={value} error={error} onChange={onChange} />;
  }

  if (type === "file" || type === "video" || type === "audio" || type === "signature") {
    return (
      <View style={{ gap: 8 }}>
        <Text style={{ fontFamily: "Manrope_600SemiBold", fontSize: 14 }}>{label}</Text>
        <Text style={{ color: "#78716C", fontSize: 13 }}>
          {type} capture is not supported on mobile yet. Complete this field on the web app.
        </Text>
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

function MediaField({
  label,
  value,
  error,
  onChange,
  mediaTypes,
}: {
  label: string;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
  mediaTypes: "images" | "videos" | "all";
}) {
  const [busy, setBusy] = useState(false);
  const val = (typeof value === "object" && value ? (value as Record<string, unknown>) : {}) as {
    uri?: string;
    local_uri?: string;
    mime_type?: string;
    file_name?: string;
    pending_upload?: boolean;
  };
  const uri = typeof val.uri === "string" ? val.uri : "";
  const pending = val.pending_upload === true;

  // Uploads bytes to object storage immediately; queues locally for retry when offline.
  async function uploadCaptured(fileUri: string, mimeType: string | undefined, fileName: string) {
    try {
      const uploaded = await api.uploadMediaBinary({
        fileUri,
        fileName,
        mimeType,
        entityType: "survey_response",
      });
      onChange({
        uri: uploaded.remote_url ?? "",
        mime_type: uploaded.mime_type ?? mimeType,
        file_name: uploaded.file_name ?? fileName,
      });
    } catch {
      try {
        await enqueueMediaUpload({
          entity_type: "survey_field",
          file_uri: fileUri,
          file_name: fileName,
          mime_type: mimeType,
        });
      } catch {
        /* best-effort local queue — capture is still preserved via local_uri below */
      }
      onChange({
        uri: "",
        local_uri: fileUri,
        mime_type: mimeType,
        file_name: fileName,
        pending_upload: true,
      });
    }
  }

  async function pick() {
    setBusy(true);
    try {
      const ImagePicker = await import("expo-image-picker");
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        onChange({ error: "Camera permission is required" });
        return;
      }
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes:
          mediaTypes === "images"
            ? ImagePicker.MediaTypeOptions.Images
            : mediaTypes === "videos"
              ? ImagePicker.MediaTypeOptions.Videos
              : ImagePicker.MediaTypeOptions.All,
        quality: 0.7,
      });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        await uploadCaptured(asset.uri, asset.mimeType, asset.fileName ?? "capture.jpg");
      }
    } catch (err) {
      onChange({ error: err instanceof Error ? err.message : "Capture failed" });
    } finally {
      setBusy(false);
    }
  }

  async function retryUpload() {
    if (!val.local_uri) return;
    setBusy(true);
    try {
      await uploadCaptured(val.local_uri, val.mime_type, val.file_name ?? "capture.jpg");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={{ gap: 8 }}>
      <Text style={{ fontFamily: "Manrope_600SemiBold", fontSize: 14 }}>{label}</Text>
      {uri ? <Text style={{ fontSize: 12, color: "#57534E" }} numberOfLines={2}>{uri}</Text> : null}
      {pending && (
        <Text style={{ fontSize: 12, color: "#B45309" }}>
          Captured — waiting to upload. Retry once you have a connection.
        </Text>
      )}
      <View style={{ flexDirection: "row", gap: 8 }}>
        <Button
          title={busy ? "Working…" : uri || pending ? "Retake photo" : "Take photo"}
          onPress={() => void pick()}
          disabled={busy}
        />
        {pending && (
          <Button title="Retry upload" variant="secondary" onPress={() => void retryUpload()} disabled={busy} />
        )}
      </View>
      {error && <Text style={{ color: "#E11D48", fontSize: 12 }}>{error}</Text>}
    </View>
  );
}

function GpsField({
  label,
  value,
  error,
  onChange,
}: {
  label: string;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
}) {
  const [busy, setBusy] = useState(false);
  const coords =
    typeof value === "object" && value
      ? (value as { lat?: number; lng?: number })
      : {};

  async function capture() {
    setBusy(true);
    try {
      const Location = await import("expo-location");
      const perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) {
        onChange({ error: "Location permission is required" });
        return;
      }
      const pos = await Location.getCurrentPositionAsync({});
      onChange({ lat: pos.coords.latitude, lng: pos.coords.longitude });
    } catch (err) {
      onChange({ error: err instanceof Error ? err.message : "Location failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={{ gap: 8 }}>
      <Text style={{ fontFamily: "Manrope_600SemiBold", fontSize: 14 }}>{label}</Text>
      {coords.lat != null && coords.lng != null ? (
        <Text style={{ fontSize: 12, color: "#57534E" }}>
          {coords.lat.toFixed(5)}, {coords.lng.toFixed(5)}
        </Text>
      ) : null}
      <Button
        title={busy ? "Locating…" : "Use current location"}
        onPress={() => void capture()}
      />
      {error && <Text style={{ color: "#E11D48", fontSize: 12 }}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  actionsRow: { flexDirection: "row", gap: 10, marginTop: 8 },
  historyRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
});
