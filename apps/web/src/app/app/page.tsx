"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckSquare,
  ClipboardCheck,
  ClipboardList,
  FolderKanban,
  GitBranch,
  HandCoins,
  Landmark,
  Layers3,
  Lightbulb,
  MapPinned,
  Sparkles,
  Target,
  UsersRound,
  Wallet,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/providers/auth-provider";

const RISK_TONE: Record<string, string> = {
  critical: "text-rose-600 dark:text-rose-400",
  high: "text-rose-600 dark:text-rose-400",
  medium: "text-amber-600 dark:text-amber-400",
  low: "text-stone-500 dark:text-stone-400",
};

function AiInsightsCard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["ai-dashboard-insights"],
    queryFn: () => api.dashboardInsights(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // Fail soft: if the endpoint errors, render nothing.
  if (isError) return null;

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            AI insights
          </CardTitle>
          <CardDescription>
            {isLoading
              ? "Scanning your portfolio…"
              : (data?.summary ?? "No insights available yet.")}
          </CardDescription>
        </div>
        <Link
          href="/app/copilot"
          className="shrink-0 text-sm font-medium text-teal-700 hover:text-teal-800 dark:text-teal-300"
        >
          Ask Copilot
        </Link>
      </div>

      {!isLoading && data && (
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <div>
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500">
              <AlertTriangle className="h-3.5 w-3.5" /> Key risks
            </p>
            <ul className="mt-2 space-y-2 text-sm">
              {data.key_risks.slice(0, 3).map((r, i) => (
                <li key={`${r.type}-${i}`} className="flex gap-2">
                  <span
                    className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-current ${
                      RISK_TONE[r.severity] ?? RISK_TONE.low
                    }`}
                  />
                  <span className="text-stone-700 dark:text-stone-300">
                    {r.title}
                  </span>
                </li>
              ))}
              {data.key_risks.length === 0 && (
                <li className="text-stone-400">No active risk signals.</li>
              )}
            </ul>
          </div>

          <div>
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500">
              <Lightbulb className="h-3.5 w-3.5" /> Recommendations
            </p>
            <ul className="mt-2 space-y-2 text-sm">
              {data.recommendations.slice(0, 3).map((rec, i) => (
                <li
                  key={i}
                  className="flex gap-2 text-stone-700 dark:text-stone-300"
                >
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="mt-5 flex flex-wrap gap-4 border-t border-stone-100 pt-4 text-sm dark:border-stone-800">
        <Link
          href="/app/predictions"
          className="inline-flex items-center gap-1 font-medium text-stone-600 hover:text-teal-700 dark:text-stone-300 dark:hover:text-teal-300"
        >
          View predictions <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <Link
          href="/app/copilot"
          className="inline-flex items-center gap-1 font-medium text-stone-600 hover:text-teal-700 dark:text-stone-300 dark:hover:text-teal-300"
        >
          Open Copilot <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.dashboardStats(),
  });

  const stats = [
    { label: "Programs", value: data?.programs_count ?? "—", icon: Layers3, href: "/app/programs" },
    { label: "Projects", value: data?.projects_count ?? "—", icon: FolderKanban, href: "/app/projects" },
    { label: "Open tasks", value: data?.open_tasks_count ?? "—", icon: CheckSquare, href: "/app/tasks" },
    { label: "Donors", value: data?.donors_count ?? "—", icon: Landmark, href: "/app/donors" },
    { label: "Active grants", value: data?.active_grants_count ?? "—", icon: HandCoins, href: "/app/grants" },
    { label: "Budgets", value: data?.budgets_count ?? "—", icon: Wallet, href: "/app/budgets" },
    {
      label: "Active beneficiaries",
      value: data?.active_beneficiaries_count ?? "—",
      icon: UsersRound,
      href: "/app/beneficiaries",
    },
    {
      label: "Communities",
      value: data?.communities_count ?? "—",
      icon: MapPinned,
      href: "/app/communities",
    },
    {
      label: "Active indicators",
      value: data?.active_indicators_count ?? "—",
      icon: Target,
      href: "/app/indicators",
    },
    {
      label: "Monitoring results",
      value: data?.monitoring_results_count ?? "—",
      icon: Activity,
      href: "/app/monitoring",
    },
    {
      label: "Surveys",
      value: data?.surveys_count ?? "—",
      icon: ClipboardList,
      href: "/app/surveys",
    },
  ];

  return (
    <div className="animate-fade-up space-y-8">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700/80 dark:text-teal-300/80">
          Overview
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 md:text-4xl">
          Welcome back, {user?.first_name}
        </h1>
        <p className="mt-2 max-w-2xl text-stone-500">
          {data?.organization.name
            ? `${data.organization.name} · Delivery, finance, and MEAL in one workspace.`
            : "Your organization workspace dashboard."}
        </p>
      </div>

      {error && (
        <Card className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
          {(error as Error).message}
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.label} href={item.href}>
              <Card className="transition-transform hover:-translate-y-0.5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-stone-500">{item.label}</p>
                    <p className="mt-3 font-display text-3xl font-semibold tracking-tight">
                      {isLoading ? "…" : item.value}
                    </p>
                  </div>
                  <div className="rounded-xl bg-teal-50 p-2 text-teal-800 dark:bg-teal-950 dark:text-teal-200">
                    <Icon className="h-4 w-4" />
                  </div>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>

      <AiInsightsCard />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>Funding snapshot</CardTitle>
          <CardDescription>Aggregated grant and expense totals.</CardDescription>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Awarded</dt>
              <dd className="font-medium">
                {isLoading ? "…" : Number(data?.grants_awarded_total ?? 0).toLocaleString()}
              </dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Received</dt>
              <dd className="font-medium">
                {isLoading ? "…" : Number(data?.grants_received_total ?? 0).toLocaleString()}
              </dd>
            </div>
            <div className="flex justify-between gap-4 py-2">
              <dt className="text-stone-500">Expenses posted</dt>
              <dd className="font-medium">
                {isLoading ? "…" : Number(data?.expenses_total ?? 0).toLocaleString()}
              </dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardTitle>MEAL snapshot</CardTitle>
          <CardDescription>Results framework and evidence pipeline.</CardDescription>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="flex items-center gap-2 text-stone-500">
                <GitBranch className="h-3.5 w-3.5" /> Theories of change
              </dt>
              <dd className="font-medium">{isLoading ? "…" : data?.theories_of_change_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Logframes</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.logframes_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Indicators</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.indicators_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Surveys</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.surveys_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 py-2">
              <dt className="flex items-center gap-2 text-stone-500">
                <ClipboardCheck className="h-3.5 w-3.5" /> Evaluations
              </dt>
              <dd className="font-medium">{isLoading ? "…" : data?.evaluations_count ?? 0}</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardTitle>Field caseload</CardTitle>
          <CardDescription>Communities, households, and enrollments.</CardDescription>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Households</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.households_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Beneficiaries</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.beneficiaries_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 py-2">
              <dt className="text-stone-500">Memberships</dt>
              <dd className="font-medium">
                {isLoading ? "…" : data?.beneficiary_memberships_count ?? 0}
              </dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardTitle>AI snapshot</CardTitle>
          <CardDescription>
            Copilot threads, open predictions, narratives, and knowledge docs.
          </CardDescription>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Conversations</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.ai_conversations_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Open predictions</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.open_predictions_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Narratives</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.ai_narratives_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 py-2">
              <dt className="text-stone-500">Knowledge docs</dt>
              <dd className="font-medium">
                {isLoading ? "…" : data?.knowledge_documents_count ?? 0}
              </dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardTitle>Platform snapshot</CardTitle>
          <CardDescription>Marketplace installs, integrations, and branding.</CardDescription>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Marketplace installs</dt>
              <dd className="font-medium">
                {isLoading ? "…" : data?.marketplace_installs_count ?? 0}
              </dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">Integrations</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.integrations_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 border-b border-stone-100 py-2 dark:border-stone-800">
              <dt className="text-stone-500">API keys</dt>
              <dd className="font-medium">{isLoading ? "…" : data?.api_keys_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-4 py-2">
              <dt className="text-stone-500">White label</dt>
              <dd className="font-medium">
                {isLoading
                  ? "…"
                  : data?.branding_enabled_count
                    ? "Enabled"
                    : "Off"}
              </dd>
            </div>
          </dl>
        </Card>
      </div>
    </div>
  );
}
