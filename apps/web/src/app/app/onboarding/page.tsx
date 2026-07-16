"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

const STEPS = [
  { id: "organization", label: "Organization", hint: "Confirm your workspace identity." },
  { id: "sector", label: "Sector", hint: "Choose the sector you operate in." },
  { id: "theme", label: "Theme", hint: "Apply a white-label theme preset." },
  { id: "project", label: "First project", hint: "Create or skip your first project." },
  { id: "invite", label: "Invite team", hint: "Bring colleagues into the workspace." },
  { id: "ai", label: "AI", hint: "Enable Copilot for your programs." },
  { id: "integrations", label: "Integrations", hint: "Connect Kobo, Slack, or Sheets." },
  { id: "notifications", label: "Notifications", hint: "Tune alerts for your team." },
];

export default function OnboardingPage() {
  const qc = useQueryClient();
  const [sector, setSector] = useState("health");
  const [country, setCountry] = useState("KE");
  const [error, setError] = useState<string | null>(null);

  const onboarding = useQuery({ queryKey: ["onboarding"], queryFn: () => api.getOnboarding() });
  const presets = useQuery({ queryKey: ["theme-presets"], queryFn: () => api.listThemePresets() });

  const update = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.updateOnboarding(body),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["onboarding"] });
      await qc.invalidateQueries({ queryKey: ["branding"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const checklist = onboarding.data?.checklist ?? {};
  const done = STEPS.filter((s) => checklist[s.id]).length;
  const complete = onboarding.data?.status === "completed";

  async function onSector(e: FormEvent) {
    e.preventDefault();
    await update.mutateAsync({
      complete_step: "sector",
      sector,
      country_code: country,
      step: "theme",
    });
  }

  return (
    <div className="animate-fade-up mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Welcome to ImpactFlow</h1>
        <p className="mt-2 text-stone-500">
          A guided setup for your organization — branding, team, AI, and integrations.
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
        {done} of {STEPS.length} steps · {onboarding.data?.current_step}
      </p>

      {complete ? (
        <Card className="border-teal-200 bg-teal-50/50 dark:border-teal-900 dark:bg-teal-950/30">
          <CardTitle>You&apos;re ready</CardTitle>
          <CardDescription>
            Workspace onboarding is complete. Continue to your dashboard or refine branding anytime.
          </CardDescription>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/app"
              className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
            >
              Open dashboard
            </Link>
            <Link
              href="/app/branding"
              className="inline-flex h-10 items-center rounded-lg bg-stone-100 px-4 text-sm font-medium text-stone-900 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-100"
            >
              White label
            </Link>
          </div>
        </Card>
      ) : (
        <>
          <Card>
            <CardTitle>Sector & country</CardTitle>
            <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={onSector}>
              <div>
                <Label htmlFor="sector">Sector</Label>
                <select
                  id="sector"
                  className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-950"
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
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
                  onChange={(e) => setCountry(e.target.value.toUpperCase())}
                />
              </div>
              <Button type="submit" disabled={update.isPending || !!checklist.sector}>
                {checklist.sector ? "Sector saved" : "Save & continue"}
              </Button>
            </form>
          </Card>

          <Card>
            <CardTitle>Theme preset</CardTitle>
            <CardDescription>Live white-label colors applied to your workspace.</CardDescription>
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
          </Card>

          <Card>
            <CardTitle>Checklist</CardTitle>
            <ul className="mt-4 space-y-2">
              {STEPS.map((step) => (
                <li
                  key={step.id}
                  className="flex items-center justify-between gap-3 rounded-xl bg-stone-50 px-3 py-2 dark:bg-stone-900"
                >
                  <div>
                    <div className="text-sm font-medium">{step.label}</div>
                    <div className="text-xs text-stone-500">{step.hint}</div>
                  </div>
                  {checklist[step.id] ? (
                    <span className="text-xs font-semibold text-teal-700">Done</span>
                  ) : (
                    <Button
                      variant="secondary"
                      onClick={() =>
                        update.mutate({
                          complete_step: step.id,
                          step: step.id,
                        })
                      }
                    >
                      Mark done
                    </Button>
                  )}
                </li>
              ))}
            </ul>
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
