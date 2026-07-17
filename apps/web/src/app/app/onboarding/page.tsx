"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

const STEPS = [
  { id: "organization", label: "Organization" },
  { id: "sector", label: "Sector" },
  { id: "theme", label: "Theme" },
  { id: "project", label: "First project" },
  { id: "invite", label: "Invite team" },
  { id: "ai", label: "AI" },
  { id: "integrations", label: "Integrations" },
  { id: "notifications", label: "Notifications" },
] as const;

const selectClassName =
  "mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-950";

function StepDone() {
  return <span className="text-xs font-semibold text-teal-700">Done</span>;
}

function SkipButton({
  disabled,
  onClick,
}: {
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <Button type="button" variant="secondary" disabled={disabled} onClick={onClick}>
      Skip for now
    </Button>
  );
}

export default function OnboardingPage() {
  const qc = useQueryClient();
  const [sector, setSector] = useState("health");
  const [country, setCountry] = useState("KE");
  const [projectName, setProjectName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onboarding = useQuery({ queryKey: ["onboarding"], queryFn: () => api.getOnboarding() });
  const presets = useQuery({ queryKey: ["theme-presets"], queryFn: () => api.listThemePresets() });
  const org = useQuery({ queryKey: ["organization"], queryFn: () => api.currentOrganization() });

  const update = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.updateOnboarding(body),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["onboarding"] });
      await qc.invalidateQueries({ queryKey: ["branding"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const createFirstProject = useMutation({
    mutationFn: async () => {
      const name = projectName.trim() || "Starter project";
      const program = await api.createProgram({
        name: `${name} program`,
        status: "active",
        goal: "Created during workspace onboarding",
      });
      const project = await api.createProject({
        program_id: program.id,
        name,
        status: "planning",
        priority: "medium",
        country_code: country || org.data?.country_code || null,
      });
      await api.updateOnboarding({
        complete_step: "project",
        step: "invite",
      });
      return project;
    },
    onSuccess: async () => {
      setProjectName("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["onboarding"] });
      await qc.invalidateQueries({ queryKey: ["projects"] });
      await qc.invalidateQueries({ queryKey: ["programs"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const checklist = onboarding.data?.checklist ?? {};
  const done = STEPS.filter((s) => checklist[s.id]).length;
  const complete = onboarding.data?.status === "completed";

  useEffect(() => {
    if (onboarding.data?.sector) setSector(onboarding.data.sector);
    if (onboarding.data?.country_code) setCountry(onboarding.data.country_code);
  }, [onboarding.data?.sector, onboarding.data?.country_code]);

  async function onSector(e: FormEvent) {
    e.preventDefault();
    await update.mutateAsync({
      complete_step: "sector",
      sector,
      country_code: country,
      step: "theme",
    });
  }

  function skip(stepId: string, next?: string) {
    update.mutate({
      complete_step: stepId,
      step: next ?? stepId,
    });
  }

  return (
    <div className="animate-fade-up mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Welcome to ImpactFlow</h1>
        <p className="mt-2 text-stone-500">
          Finish these setup steps so your team can invite field officers, assign work, and sync
          from mobile.
        </p>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="h-2 overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800">
        <div
          className="h-full rounded-full bg-teal-700 transition-all duration-500"
          style={{ width: `${Math.round((done / STEPS.length) * 100)}%` }}
        />
      </div>
      <p className="text-sm text-stone-500">
        {done} of {STEPS.length} steps
        {onboarding.data?.current_step ? ` · current: ${onboarding.data.current_step}` : ""}
      </p>

      {complete ? (
        <Card className="border-teal-200 bg-teal-50/50 dark:border-teal-900 dark:bg-teal-950/30">
          <CardTitle>You&apos;re ready</CardTitle>
          <CardDescription>
            Workspace onboarding is complete. Invite teammates, assign project tasks, and open the
            field app with the same login.
          </CardDescription>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/app"
              className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
            >
              Open dashboard
            </Link>
            <Link
              href="/app/users"
              className="inline-flex h-10 items-center rounded-lg bg-stone-100 px-4 text-sm font-medium text-stone-900 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-100"
            >
              Invite team
            </Link>
          </div>
        </Card>
      ) : (
        <>
          <Card>
            <CardTitle>1. Organization</CardTitle>
            <CardDescription>
              Confirm your workspace identity. You can edit details anytime.
            </CardDescription>
            <div className="mt-4 rounded-xl bg-stone-50 px-3 py-3 text-sm dark:bg-stone-900">
              <p className="font-medium">{org.data?.name ?? "Loading…"}</p>
              <p className="text-stone-500">
                {org.data?.slug ? `/${org.data.slug}` : ""}
                {org.data?.organization_type ? ` · ${org.data.organization_type}` : ""}
              </p>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {checklist.organization ? (
                <StepDone />
              ) : (
                <>
                  <Button
                    disabled={update.isPending || !org.data}
                    onClick={() =>
                      update.mutate({
                        complete_step: "organization",
                        step: "sector",
                      })
                    }
                  >
                    Confirm organization
                  </Button>
                  <Link
                    href="/app/organization"
                    className="inline-flex h-10 items-center rounded-lg bg-stone-100 px-4 text-sm font-medium text-stone-900 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-100"
                  >
                    Edit profile
                  </Link>
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardTitle>2. Sector & country</CardTitle>
            <CardDescription>Used for recommendations and default project country.</CardDescription>
            <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={onSector}>
              <div>
                <Label htmlFor="sector">Sector</Label>
                <select
                  id="sector"
                  className={selectClassName}
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
                  disabled={!!checklist.sector}
                >
                  {["health", "education", "wash", "agriculture", "governance", "humanitarian"].map(
                    (s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ),
                  )}
                </select>
              </div>
              <div>
                <Label htmlFor="country">Country (ISO)</Label>
                <Input
                  id="country"
                  value={country}
                  maxLength={2}
                  disabled={!!checklist.sector}
                  onChange={(e) => setCountry(e.target.value.toUpperCase())}
                />
              </div>
              <div className="sm:col-span-2">
                {checklist.sector ? (
                  <StepDone />
                ) : (
                  <Button type="submit" disabled={update.isPending}>
                    Save & continue
                  </Button>
                )}
              </div>
            </form>
          </Card>

          <Card>
            <CardTitle>3. Theme</CardTitle>
            <CardDescription>Apply a white-label color preset to your workspace.</CardDescription>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(presets.data?.items ?? []).map((t) => (
                <button
                  key={t.code}
                  type="button"
                  disabled={update.isPending}
                  onClick={() =>
                    update.mutate({
                      complete_step: "theme",
                      theme_preset: t.code,
                      step: "project",
                    })
                  }
                  className="rounded-2xl border border-stone-200 p-4 text-left transition hover:border-teal-600 dark:border-stone-800"
                >
                  <div className="flex gap-2">
                    {[t.primary, t.secondary, t.accent].map((c) => (
                      <span
                        key={c}
                        className="h-6 w-6 rounded-full border border-white/40"
                        style={{ background: c }}
                      />
                    ))}
                  </div>
                  <div className="mt-2 font-medium">{t.name}</div>
                  {onboarding.data?.theme_preset === t.code && (
                    <div className="mt-1 text-xs text-teal-700">Applied</div>
                  )}
                </button>
              ))}
            </div>
            {checklist.theme ? (
              <div className="mt-3">
                <StepDone />
              </div>
            ) : null}
          </Card>

          <Card>
            <CardTitle>4. First project</CardTitle>
            <CardDescription>
              Creates a starter program and project so you can assign tasks to field officers.
            </CardDescription>
            {checklist.project ? (
              <div className="mt-4">
                <StepDone />
              </div>
            ) : (
              <form
                className="mt-4 space-y-3"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  createFirstProject.mutate();
                }}
              >
                <div>
                  <Label htmlFor="project-name">Project name</Label>
                  <Input
                    id="project-name"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="e.g. County A field rollout"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" disabled={createFirstProject.isPending}>
                    {createFirstProject.isPending ? "Creating…" : "Create project"}
                  </Button>
                  <SkipButton
                    disabled={update.isPending}
                    onClick={() => skip("project", "invite")}
                  />
                </div>
              </form>
            )}
          </Card>

          <Card>
            <CardTitle>5. Invite team</CardTitle>
            <CardDescription>
              Invite Field Officers for mobile sync, or Managers for programs. Each member uses one
              billing seat.
            </CardDescription>
            <div className="mt-4 flex flex-wrap gap-2">
              {checklist.invite ? (
                <StepDone />
              ) : (
                <>
                  <Link
                    href="/app/users"
                    className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
                    onClick={() =>
                      update.mutate({
                        complete_step: "invite",
                        step: "ai",
                      })
                    }
                  >
                    Invite teammates
                  </Link>
                  <SkipButton disabled={update.isPending} onClick={() => skip("invite", "ai")} />
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardTitle>6. AI Copilot</CardTitle>
            <CardDescription>
              Explore AI-assisted drafts for programs, surveys, and reports.
            </CardDescription>
            <div className="mt-4 flex flex-wrap gap-2">
              {checklist.ai ? (
                <StepDone />
              ) : (
                <>
                  <Link
                    href="/app/copilot"
                    className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
                    onClick={() =>
                      update.mutate({
                        complete_step: "ai",
                        step: "integrations",
                      })
                    }
                  >
                    Open Copilot
                  </Link>
                  <SkipButton
                    disabled={update.isPending}
                    onClick={() => skip("ai", "integrations")}
                  />
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardTitle>7. Integrations</CardTitle>
            <CardDescription>
              Connect tools like Kobo, Slack, or Sheets when you are ready.
            </CardDescription>
            <div className="mt-4 flex flex-wrap gap-2">
              {checklist.integrations ? (
                <StepDone />
              ) : (
                <>
                  <Link
                    href="/app/integrations"
                    className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
                    onClick={() =>
                      update.mutate({
                        complete_step: "integrations",
                        step: "notifications",
                      })
                    }
                  >
                    Open integrations
                  </Link>
                  <SkipButton
                    disabled={update.isPending}
                    onClick={() => skip("integrations", "notifications")}
                  />
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardTitle>8. Notifications</CardTitle>
            <CardDescription>Review alerts for invites, tasks, and field sync events.</CardDescription>
            <div className="mt-4 flex flex-wrap gap-2">
              {checklist.notifications ? (
                <StepDone />
              ) : (
                <>
                  <Link
                    href="/app/notifications"
                    className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
                    onClick={() =>
                      update.mutate({
                        complete_step: "notifications",
                        step: "complete",
                      })
                    }
                  >
                    Open notifications
                  </Link>
                  <SkipButton
                    disabled={update.isPending}
                    onClick={() => skip("notifications", "complete")}
                  />
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardTitle>Finish setup</CardTitle>
            <CardDescription>
              You can return to onboarding later from the workspace menu.
            </CardDescription>
            <Button
              className="mt-4"
              disabled={update.isPending}
              onClick={() => update.mutate({ mark_complete: true })}
            >
              Celebrate & finish
            </Button>
          </Card>
        </>
      )}
    </div>
  );
}
