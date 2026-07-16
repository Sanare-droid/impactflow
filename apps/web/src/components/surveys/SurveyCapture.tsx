"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Survey, type SurveyVersionDetail } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { SurveyFormRenderer } from "./SurveyFormRenderer";
import { newId, normalizeSchemaForClient } from "./schema-utils";

export function SurveyCapture({ survey, version }: { survey: Survey; version: SurveyVersionDetail }) {
  const qc = useQueryClient();
  const schema = useMemo(() => normalizeSchemaForClient(version.schema), [version.id]);
  const pages = schema.pages || [];
  const settings = schema.settings || {};

  const [pageIndex, setPageIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [respondent, setRespondent] = useState("");
  const [responseId, setResponseId] = useState<string | null>(null);
  const [clientMutationId, setClientMutationId] = useState(() => newId("resp"));
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const canAcceptResponses = survey.status === "published";
  const showProgress = settings.progress_bar !== false && pages.length > 1;

  const resetForm = () => {
    setAnswers({});
    setRespondent("");
    setResponseId(null);
    setPageIndex(0);
    setClientMutationId(newId("resp"));
  };

  const buildBody = (status: "draft" | "submitted") => ({
    answers,
    status,
    respondent_name: survey.is_anonymous ? undefined : respondent || undefined,
  });

  const saveDraft = useMutation({
    mutationFn: () =>
      responseId
        ? api.updateSurveyResponse(responseId, buildBody("draft"))
        : api.submitSurveyResponse(survey.id, { ...buildBody("draft"), client_mutation_id: clientMutationId }),
    onSuccess: async (resp) => {
      setResponseId(resp.id);
      setNotice("Draft saved.");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["survey-responses", survey.id] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const submit = useMutation({
    mutationFn: () =>
      responseId
        ? api.updateSurveyResponse(responseId, buildBody("submitted"))
        : api.submitSurveyResponse(survey.id, { ...buildBody("submitted"), client_mutation_id: clientMutationId }),
    onSuccess: async () => {
      resetForm();
      setNotice("Response submitted. Thank you!");
      setError(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["survey-responses", survey.id] }),
        qc.invalidateQueries({ queryKey: ["survey-analytics", survey.id] }),
      ]);
    },
    onError: (err: Error) => setError(err.message),
  });

  const currentPage = pages[pageIndex];
  const isLastPage = pageIndex === pages.length - 1;

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <CardTitle>Capture response</CardTitle>
          <CardDescription>Submit answers against the current published schema.</CardDescription>
        </div>
        {!canAcceptResponses && (
          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-200">
            Survey must be published to accept responses
          </span>
        )}
      </div>

      {showProgress && (
        <div className="mt-4">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-stone-100 dark:bg-stone-800">
            <div
              className="h-full rounded-full bg-teal-600 transition-all"
              style={{ width: `${((pageIndex + 1) / pages.length) * 100}%` }}
            />
          </div>
          <p className="mt-1.5 text-xs text-stone-400">
            Page {pageIndex + 1} of {pages.length}
            {currentPage?.title ? ` · ${currentPage.title}` : ""}
          </p>
        </div>
      )}

      <div className="mt-4 space-y-4">
        {pageIndex === 0 && !survey.is_anonymous && (
          <div>
            <Label htmlFor="respondent">Respondent name</Label>
            <Input id="respondent" value={respondent} onChange={(e) => setRespondent(e.target.value)} />
          </div>
        )}

        {currentPage && (
          <SurveyFormRenderer
            page={currentPage}
            answers={answers}
            onChange={(fieldId, value) => setAnswers((prev) => ({ ...prev, [fieldId]: value }))}
          />
        )}

        {error && <p className="text-sm text-rose-600">{error}</p>}
        {notice && <p className="text-sm text-teal-700 dark:text-teal-300">{notice}</p>}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={pageIndex === 0}
            onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
          >
            Previous
          </Button>
          <div className="flex items-center gap-2">
            {settings.allow_draft !== false && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!canAcceptResponses || saveDraft.isPending}
                onClick={() => saveDraft.mutate()}
              >
                {saveDraft.isPending ? "Saving…" : "Save draft"}
              </Button>
            )}
            {isLastPage ? (
              <Button type="button" size="sm" disabled={!canAcceptResponses || submit.isPending} onClick={() => submit.mutate()}>
                {submit.isPending ? "Submitting…" : "Submit response"}
              </Button>
            ) : (
              <Button type="button" size="sm" onClick={() => setPageIndex((p) => Math.min(pages.length - 1, p + 1))}>
                Next
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
