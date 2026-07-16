"use client";

import { useState } from "react";
import { Sparkles, X } from "lucide-react";
import { api, type WorkflowDefinition } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { CardTitle } from "@/components/ui/card";

const textareaClass =
  "w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100";

export function AiAssistDialog({
  open,
  onClose,
  onApply,
}: {
  open: boolean;
  onClose: () => void;
  onApply: (definition: WorkflowDefinition) => void;
}) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<{
    definition: WorkflowDefinition;
    explanation: string;
  } | null>(null);

  if (!open) return null;

  const reset = () => {
    setPrompt("");
    setDraft(null);
    setError(null);
    setLoading(false);
  };

  const close = () => {
    reset();
    onClose();
  };

  const generate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.draftAiWorkflow(prompt.trim(), false);
      setDraft({ definition: result.definition, explanation: result.explanation });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft failed");
    } finally {
      setLoading(false);
    }
  };

  const apply = () => {
    if (!draft) return;
    onApply(draft.definition);
    close();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-stone-900/40 backdrop-blur-sm"
        onClick={close}
      />
      <div className="relative z-10 w-full max-w-lg rounded-2xl border border-stone-200/80 bg-white p-5 shadow-xl dark:border-stone-800 dark:bg-stone-950">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-700 text-white dark:bg-teal-600">
              <Sparkles className="h-4 w-4" />
            </span>
            <CardTitle className="text-base">AI Assist</CardTitle>
          </div>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            onClick={close}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <p className="mt-2 text-sm text-stone-500">
          Describe the automation you want. The draft replaces the current builder
          definition when applied.
        </p>

        <textarea
          className={`${textareaClass} mt-3`}
          rows={4}
          placeholder="e.g. When a survey response is submitted, notify managers and create a follow-up task."
          value={prompt}
          disabled={loading}
          onChange={(e) => setPrompt(e.target.value)}
        />

        {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}

        {draft && (
          <div className="mt-3 space-y-2 rounded-xl border border-stone-100 bg-stone-50/70 p-3 dark:border-stone-900 dark:bg-stone-900/40">
            <p className="text-xs font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400">
              Proposed draft
            </p>
            {draft.explanation && (
              <p className="text-sm text-stone-600 dark:text-stone-300">
                {draft.explanation}
              </p>
            )}
            <p className="text-xs text-stone-400">
              Trigger: {draft.definition.trigger?.type ?? "manual"} ·{" "}
              {draft.definition.actions?.length ?? 0} action
              {(draft.definition.actions?.length ?? 0) === 1 ? "" : "s"}
            </p>
          </div>
        )}

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button type="button" variant="ghost" onClick={close}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={loading || !prompt.trim()}
            onClick={generate}
          >
            {loading ? "Drafting…" : draft ? "Regenerate" : "Generate draft"}
          </Button>
          {draft && (
            <Button type="button" onClick={apply}>
              Apply to builder
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
