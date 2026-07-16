"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Survey } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const TARGET_TYPES = [
  "program",
  "project",
  "activity",
  "beneficiary",
  "community",
  "household",
] as const;

export function SurveyAssignments({ survey }: { survey: Survey }) {
  const qc = useQueryClient();
  const [targetType, setTargetType] = useState<(typeof TARGET_TYPES)[number]>("project");
  const [targetId, setTargetId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["survey-assignments", survey.id],
    queryFn: () => api.listAssignments(survey.id),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createAssignment(survey.id, {
        target_type: targetType,
        target_id: targetId.trim(),
      }),
    onSuccess: async () => {
      setTargetId("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["survey-assignments", survey.id] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const remove = useMutation({
    mutationFn: (assignmentId: string) => api.deleteAssignment(survey.id, assignmentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["survey-assignments", survey.id] }),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardTitle>Assign form</CardTitle>
        <CardDescription>
          Share this form with a program, project, activity, beneficiary, community, or household.
        </CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="target-type">Target type</Label>
            <select
              id="target-type"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={targetType}
              onChange={(e) => setTargetType(e.target.value as (typeof TARGET_TYPES)[number])}
            >
              {TARGET_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="target-id">Target ID</Label>
            <Input
              id="target-id"
              required
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              placeholder="UUID of the related record"
            />
          </div>
          <div className="md:col-span-3">
            <Button type="submit" disabled={create.isPending || !targetId.trim()}>
              {create.isPending ? "Assigning…" : "Add assignment"}
            </Button>
          </div>
        </form>
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Card>

      <Card>
        <CardTitle>Current assignments</CardTitle>
        <div className="mt-4 space-y-3">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {!isLoading && (data?.length ?? 0) === 0 && (
            <EmptyState
              title="No assignments yet"
              description="Assign this form so field teams know where it applies."
            />
          )}
          {data?.map((row) => (
            <div
              key={row.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
            >
              <div>
                <p className="font-medium capitalize">{row.target_type}</p>
                <p className="font-mono text-xs text-stone-500">{row.target_id}</p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={row.status} />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(row.id)}
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
