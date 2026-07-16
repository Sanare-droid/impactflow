"use client";

import { FormEvent, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

type Field = {
  id: string;
  type: string;
  label: string;
  required?: boolean;
  options?: string[];
};

export default function SurveyDetailPage() {
  const params = useParams<{ id: string }>();
  const surveyId = params.id;
  const qc = useQueryClient();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [respondent, setRespondent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["survey", surveyId],
    queryFn: () => api.getSurvey(surveyId),
  });

  const responses = useQuery({
    queryKey: ["survey-responses", surveyId],
    queryFn: () => api.listSurveyResponses({ survey_id: surveyId }),
  });

  const fields: Field[] = useMemo(
    () => (data?.version.schema?.fields as Field[]) || [],
    [data],
  );

  const submit = useMutation({
    mutationFn: () =>
      api.submitSurveyResponse(surveyId, {
        answers,
        respondent_name: respondent || undefined,
      }),
    onSuccess: async () => {
      setAnswers({});
      setRespondent("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["survey-responses", surveyId] });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (isLoading || !data) {
    return <p className="text-stone-400">Loading…</p>;
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          {data.survey.name}
        </h1>
        <p className="mt-2 flex items-center gap-2 text-stone-500">
          {data.survey.code} · v{data.version.version}
          <StatusBadge status={data.survey.status} />
        </p>
      </div>

      <Card>
        <CardTitle>Capture response</CardTitle>
        <CardDescription>Submit answers against the current schema version.</CardDescription>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            submit.mutate();
          }}
        >
          <div>
            <Label htmlFor="respondent">Respondent name</Label>
            <Input
              id="respondent"
              value={respondent}
              onChange={(e) => setRespondent(e.target.value)}
            />
          </div>
          {fields.map((field) => (
            <div key={field.id}>
              <Label htmlFor={field.id}>
                {field.label}
                {field.required ? " *" : ""}
              </Label>
              {field.type === "select" ? (
                <select
                  id={field.id}
                  className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                  value={answers[field.id] || ""}
                  required={field.required}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [field.id]: e.target.value }))
                  }
                >
                  <option value="">Select…</option>
                  {(field.options || []).map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  id={field.id}
                  required={field.required}
                  value={answers[field.id] || ""}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [field.id]: e.target.value }))
                  }
                />
              )}
            </div>
          ))}
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <Button type="submit" disabled={submit.isPending}>
            {submit.isPending ? "Submitting…" : "Submit response"}
          </Button>
        </form>
      </Card>

      <Card>
        <CardTitle>Recent responses</CardTitle>
        <div className="mt-4 space-y-2">
          {(responses.data?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">No responses yet.</p>
          )}
          {responses.data?.items.map((r) => (
            <div
              key={r.id}
              className="rounded-xl border border-stone-100 px-4 py-3 text-sm dark:border-stone-900"
            >
              <p className="font-medium">{r.respondent_name || "Anonymous"}</p>
              <p className="text-xs text-stone-500">
                {new Date(r.created_at).toLocaleString()} · {r.status}
              </p>
              <pre className="mt-2 overflow-x-auto text-xs text-stone-600 dark:text-stone-400">
                {JSON.stringify(r.answers, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
