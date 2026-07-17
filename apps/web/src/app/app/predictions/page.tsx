"use client";

import { FeatureGate } from "@/components/feature-gate";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

export default function PredictionsPage() {
  return (
    <FeatureGate feature="ai" fallbackTitle="Predictions require Starter+">
      <PredictionsInner />
    </FeatureGate>
  );
}

function PredictionsInner() {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["ai-predictions"],
    queryFn: () => api.listAiPredictions(),
  });

  const generate = useMutation({
    mutationFn: () => api.generateAiPrediction({ prediction_type: "project_risk" }),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["ai-predictions"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const acknowledge = useMutation({
    mutationFn: (id: string) => api.updateAiPrediction(id, { status: "acknowledged" }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["ai-predictions"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Predictions</h1>
          <p className="mt-2 text-stone-500">
            Portfolio risk and delivery signals generated from live MEAL and finance counts.
          </p>
        </div>
        <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
          {generate.isPending ? "Scanning…" : "Run risk scan"}
        </Button>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <Card>
        <CardTitle>Risk register</CardTitle>
        <CardDescription>Open and acknowledged predictions for this organization.</CardDescription>
        <div className="mt-4 space-y-4">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {data?.items.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-stone-200 p-4 dark:border-stone-800"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-medium">{item.title}</h3>
                  <p className="mt-1 text-sm text-stone-500">{item.summary}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status={item.severity} />
                  <StatusBadge status={item.status} />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-stone-400">
                <span>Score {String(item.score)}</span>
                <span>{item.provider}</span>
                <span>{item.prediction_type}</span>
              </div>
              {item.recommendations?.length > 0 && (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-stone-600 dark:text-stone-300">
                  {item.recommendations.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
              {item.status === "open" && (
                <div className="mt-3">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => acknowledge.mutate(item.id)}
                    disabled={acknowledge.isPending}
                  >
                    Acknowledge
                  </Button>
                </div>
              )}
            </div>
          ))}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">No predictions yet. Run a risk scan.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
