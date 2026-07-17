"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Survey } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const TARGET_TYPES = [
  "program",
  "project",
  "activity",
  "beneficiary",
  "community",
  "household",
] as const;

type Option = { id: string; label: string };

export function SurveyAssignments({ survey }: { survey: Survey }) {
  const qc = useQueryClient();
  const [targetType, setTargetType] = useState<(typeof TARGET_TYPES)[number]>("project");
  const [targetId, setTargetId] = useState("");
  const [activityProjectId, setActivityProjectId] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["survey-assignments", survey.id],
    queryFn: () => api.listAssignments(survey.id),
  });

  const programs = useQuery({
    queryKey: ["programs-picker"],
    queryFn: () => api.listPrograms({ page: 1 }),
    enabled: targetType === "program",
  });
  const projects = useQuery({
    queryKey: ["projects-picker"],
    queryFn: () => api.listProjects({ page: 1 }),
    enabled: targetType === "project" || targetType === "activity",
  });
  const activities = useQuery({
    queryKey: ["activities-picker", activityProjectId],
    queryFn: () => api.listActivities(activityProjectId),
    enabled: targetType === "activity" && Boolean(activityProjectId),
  });
  const beneficiaries = useQuery({
    queryKey: ["beneficiaries-picker"],
    queryFn: () => api.listBeneficiaries(),
    enabled: targetType === "beneficiary",
  });
  const communities = useQuery({
    queryKey: ["communities-picker"],
    queryFn: () => api.listCommunities(),
    enabled: targetType === "community",
  });
  const households = useQuery({
    queryKey: ["households-picker"],
    queryFn: () => api.listHouseholds(),
    enabled: targetType === "household",
  });

  const options: Option[] = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filter = (items: Option[]) =>
      q ? items.filter((o) => o.label.toLowerCase().includes(q)) : items;

    if (targetType === "program") {
      return filter(
        (programs.data?.items ?? []).map((p) => ({
          id: p.id,
          label: `${p.name}${p.code ? ` (${p.code})` : ""}`,
        })),
      );
    }
    if (targetType === "project") {
      return filter(
        (projects.data?.items ?? []).map((p) => ({
          id: p.id,
          label: `${p.name}${p.code ? ` (${p.code})` : ""}`,
        })),
      );
    }
    if (targetType === "activity") {
      return filter(
        (activities.data?.items ?? []).map((a) => ({
          id: a.id,
          label: `${a.name}${a.code ? ` (${a.code})` : ""}`,
        })),
      );
    }
    if (targetType === "beneficiary") {
      return filter(
        (beneficiaries.data?.items ?? []).map((b) => ({
          id: b.id,
          label: `${b.first_name} ${b.last_name}${b.code ? ` (${b.code})` : ""}`,
        })),
      );
    }
    if (targetType === "community") {
      return filter(
        (communities.data?.items ?? []).map((c) => ({
          id: c.id,
          label: `${c.name}${c.code ? ` (${c.code})` : ""}`,
        })),
      );
    }
    return filter(
      (households.data?.items ?? []).map((h) => ({
        id: h.id,
        label: `${h.name}${h.code ? ` (${h.code})` : ""}`,
      })),
    );
  }, [
    targetType,
    search,
    programs.data,
    projects.data,
    activities.data,
    beneficiaries.data,
    communities.data,
    households.data,
  ]);

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

  const selectClass =
    "mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950";

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
              className={selectClass}
              value={targetType}
              onChange={(e) => {
                setTargetType(e.target.value as (typeof TARGET_TYPES)[number]);
                setTargetId("");
                setActivityProjectId("");
                setSearch("");
              }}
            >
              {TARGET_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          {targetType === "activity" ? (
            <div>
              <Label htmlFor="activity-project">Project</Label>
              <select
                id="activity-project"
                className={selectClass}
                value={activityProjectId}
                onChange={(e) => {
                  setActivityProjectId(e.target.value);
                  setTargetId("");
                }}
                required
              >
                <option value="">Select project…</option>
                {(projects.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
          <div className={targetType === "activity" ? "" : "md:col-span-2"}>
            <Label htmlFor="target-search">Search</Label>
            <input
              id="target-search"
              className={selectClass}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by name or code"
            />
          </div>
          <div className="md:col-span-3">
            <Label htmlFor="target-id">Record</Label>
            <select
              id="target-id"
              className={selectClass}
              required
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              disabled={targetType === "activity" && !activityProjectId}
            >
              <option value="">
                {options.length === 0 ? "No matching records" : "Select record…"}
              </option>
              {options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
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
