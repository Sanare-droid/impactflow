"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  FileText,
  Gauge,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

const SEVERITY_TONE: Record<string, string> = {
  critical: "bg-rose-500",
  high: "bg-rose-500",
  medium: "bg-amber-500",
  low: "bg-stone-400",
};

const HEALTH_RING: Record<string, string> = {
  healthy: "stroke-teal-600 dark:stroke-teal-400",
  watch: "stroke-amber-500 dark:stroke-amber-400",
  at_risk: "stroke-rose-500 dark:stroke-rose-400",
};

function formatNum(value: number | undefined | null, digits = 0) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function formatPct(value: number | undefined | null) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${formatNum(value, 1)}%`;
}

function ProgressBar({
  value,
  max = 100,
  className,
}: {
  value: number;
  max?: number;
  className?: string;
}) {
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-stone-100 dark:bg-stone-800">
      <div
        className={cn("h-full rounded-full bg-teal-600 transition-all dark:bg-teal-500", className)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function HealthRing({ score, band }: { score: number; band: string }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  const clamped = Math.min(100, Math.max(0, score));
  const offset = c - (clamped / 100) * c;
  const stroke = HEALTH_RING[band] ?? HEALTH_RING.watch;

  return (
    <div className="relative mx-auto flex h-40 w-40 items-center justify-center">
      <svg className="-rotate-90" width="160" height="160" viewBox="0 0 160 160">
        <circle
          cx="80"
          cy="80"
          r={r}
          fill="none"
          strokeWidth="10"
          className="stroke-stone-100 dark:stroke-stone-800"
        />
        <circle
          cx="80"
          cy="80"
          r={r}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className={cn("transition-all duration-700", stroke)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-4xl font-semibold tabular-nums tracking-tight">
          {formatNum(score, 1)}
        </span>
        <span className="mt-0.5 text-xs font-medium uppercase tracking-wider text-stone-500">
          {band.replaceAll("_", " ")}
        </span>
      </div>
    </div>
  );
}

function KpiTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-stone-100 bg-stone-50/60 px-3 py-3 dark:border-stone-800 dark:bg-stone-900/40">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold tabular-nums tracking-tight text-stone-900 dark:text-stone-50">
        {value}
      </p>
      {hint ? <p className="mt-0.5 text-xs text-stone-400">{hint}</p> : null}
    </div>
  );
}

const DETAIL_TABS = [
  { id: "portfolio", label: "Portfolio" },
  { id: "compliance", label: "Compliance" },
  { id: "impact", label: "Impact" },
  { id: "risks", label: "Risks" },
];

export default function ExecutivePage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("portfolio");
  const [briefAudience, setBriefAudience] = useState("board");
  const [error, setError] = useState<string | null>(null);
  const [briefPreview, setBriefPreview] = useState<string | null>(null);

  const dash = useQuery({
    queryKey: ["executive-dashboard"],
    queryFn: () => api.executiveDashboard(),
  });

  const portfolio = useQuery({
    queryKey: ["executive-portfolio"],
    queryFn: () => api.executivePortfolio(),
    enabled: tab === "portfolio",
  });

  const compliance = useQuery({
    queryKey: ["executive-compliance"],
    queryFn: () => api.executiveCompliance(),
    enabled: tab === "compliance",
  });

  const impact = useQuery({
    queryKey: ["executive-impact"],
    queryFn: () => api.executiveImpact(),
    enabled: tab === "impact",
  });

  const risks = useQuery({
    queryKey: ["executive-risks"],
    queryFn: () => api.executiveRisks(),
    enabled: tab === "risks",
  });

  const brief = useMutation({
    mutationFn: () =>
      api.createExecutiveBrief({
        audience: briefAudience,
        save_as_report: true,
      }),
    onSuccess: async (res) => {
      setError(null);
      const content =
        typeof res.narrative === "object" && res.narrative && "content" in res.narrative
          ? String((res.narrative as { content?: string }).content ?? "")
          : "";
      setBriefPreview(content.slice(0, 1200) || "Brief generated and saved as a report.");
      await qc.invalidateQueries({ queryKey: ["executive-dashboard"] });
      await qc.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const data = dash.data;
  const kpis = data?.kpis;
  const female = kpis?.female ?? 0;
  const male = kpis?.male ?? 0;
  const genderTotal = female + male + (kpis?.other ?? 0) + (kpis?.unknown ?? 0);
  const femalePct = genderTotal > 0 ? (female / genderTotal) * 100 : 0;

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Executive</h1>
          <p className="mt-2 max-w-2xl text-stone-500">
            Portfolio health, impact reach, compliance gaps, and one-click briefs for leadership.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
            value={briefAudience}
            onChange={(e) => setBriefAudience(e.target.value)}
            aria-label="Brief audience"
          >
            <option value="board">Board</option>
            <option value="donor">Donor</option>
            <option value="management">Management</option>
            <option value="government">Government</option>
            <option value="investor">Investor</option>
          </select>
          <Button disabled={brief.isPending} onClick={() => brief.mutate()}>
            <Sparkles className="h-4 w-4" />
            {brief.isPending ? "Generating…" : "Generate brief"}
          </Button>
          <Link href="/app/reports">
            <Button variant="secondary">
              <FileText className="h-4 w-4" />
              Open reports
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </p>
      )}

      {briefPreview && (
        <Card className="border-teal-200/80 bg-teal-50/40 dark:border-teal-900 dark:bg-teal-950/20">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-teal-600" />
            Latest brief preview
          </CardTitle>
          <p className="mt-3 whitespace-pre-wrap text-sm text-stone-700 dark:text-stone-300">
            {briefPreview}
            {briefPreview.length >= 1200 ? "…" : ""}
          </p>
          <Link
            href="/app/reports"
            className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-teal-700 dark:text-teal-300"
          >
            View in reports <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Card>
      )}

      {dash.isLoading && <p className="text-sm text-stone-400">Loading executive dashboard…</p>}

      {dash.isError && (
        <Card className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
          {(dash.error as Error).message}
        </Card>
      )}

      {data && kpis && (
        <>
          <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
            <Card className="flex flex-col items-center justify-center">
              <div className="mb-2 flex items-center gap-2 self-start">
                <Gauge className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                <CardTitle className="text-base">Portfolio health</CardTitle>
              </div>
              <HealthRing score={data.portfolio_health.score} band={data.portfolio_health.band} />
              <dl className="mt-4 grid w-full grid-cols-2 gap-2 text-xs">
                {Object.entries(data.portfolio_health.components).map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-stone-50 px-2 py-1.5 dark:bg-stone-900/50">
                    <dt className="capitalize text-stone-500">{k.replaceAll("_", " ")}</dt>
                    <dd className="font-medium tabular-nums">{formatNum(v, 1)}</dd>
                  </div>
                ))}
              </dl>
            </Card>

            <Card>
              <CardTitle>Key performance</CardTitle>
              <CardDescription>
                Programs, finance burn, and inclusion reach across the portfolio.
              </CardDescription>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <KpiTile label="Programs" value={formatNum(kpis.active_programs)} />
                <KpiTile label="Projects" value={formatNum(kpis.active_projects)} />
                <KpiTile
                  label="Active grants"
                  value={formatNum(kpis.active_grants)}
                  hint={`${formatNum(kpis.grant_pipeline)} in pipeline`}
                />
                <KpiTile
                  label="Budget burn"
                  value={formatPct(kpis.budget_utilization_pct)}
                />
                <KpiTile
                  label="Beneficiaries"
                  value={formatNum(kpis.beneficiary_reach)}
                  hint={`${formatNum(kpis.active_beneficiaries)} active`}
                />
                <KpiTile
                  label="Female reach"
                  value={formatPct(femalePct)}
                  hint={`${formatNum(female)} / ${formatNum(genderTotal)}`}
                />
                <KpiTile label="Youth" value={formatNum(kpis.youth_reach)} />
                <KpiTile
                  label="Persons with disabilities"
                  value={formatNum(kpis.persons_with_disabilities)}
                />
                <KpiTile
                  label="Communities"
                  value={formatNum(kpis.communities_reached)}
                />
              </div>
            </Card>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <Card className="xl:col-span-1">
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                Risk heat
              </CardTitle>
              <CardDescription>Highest-severity portfolio signals.</CardDescription>
              <ul className="mt-4 space-y-3">
                {data.risk_heat.length === 0 && (
                  <EmptyState title="No risk signals" description="Portfolio looks quiet right now." />
                )}
                {data.risk_heat.slice(0, 6).map((r, i) => (
                  <li
                    key={`${r.type}-${i}`}
                    className="rounded-xl border border-stone-100 px-3 py-2.5 dark:border-stone-800"
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className={cn(
                          "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                          SEVERITY_TONE[r.severity ?? "low"] ?? SEVERITY_TONE.low,
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-stone-900 dark:text-stone-100">
                          {r.title ?? "Risk"}
                        </p>
                        {r.summary ? (
                          <p className="mt-0.5 line-clamp-2 text-xs text-stone-500">{r.summary}</p>
                        ) : null}
                      </div>
                      <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-stone-400">
                        {r.severity}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="xl:col-span-1">
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-teal-600" />
                AI insights
              </CardTitle>
              <CardDescription>
                {data.ai_insights.summary ?? "Grounded recommendations from live records."}
              </CardDescription>
              <div className="mt-4 space-y-4">
                <div>
                  <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500">
                    <Lightbulb className="h-3.5 w-3.5" /> Recommendations
                  </p>
                  <ul className="mt-2 space-y-2 text-sm text-stone-700 dark:text-stone-300">
                    {(data.ai_insights.recommendations ?? []).slice(0, 4).map((rec, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                        {rec}
                      </li>
                    ))}
                    {(data.ai_insights.recommendations ?? []).length === 0 && (
                      <li className="text-stone-400">No recommendations yet.</li>
                    )}
                  </ul>
                </div>
                {(data.ai_insights.wins ?? []).length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                      Wins
                    </p>
                    <ul className="mt-2 space-y-1.5 text-sm text-stone-700 dark:text-stone-300">
                      {(data.ai_insights.wins ?? []).map((w, i) => (
                        <li key={i}>• {w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>

            <Card className="xl:col-span-1">
              <CardTitle>Upcoming deadlines</CardTitle>
              <CardDescription>Grants ending soon and overdue tasks.</CardDescription>
              <div className="mt-4 space-y-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                    Grants expiring
                  </p>
                  <ul className="mt-2 space-y-2">
                    {data.upcoming_deadlines.grants_expiring.length === 0 && (
                      <li className="text-sm text-stone-400">None in the next 90 days.</li>
                    )}
                    {data.upcoming_deadlines.grants_expiring.slice(0, 4).map((g) => (
                      <li key={g.id} className="flex items-center justify-between gap-2 text-sm">
                        <span className="truncate font-medium">{g.name}</span>
                        <span className="shrink-0 tabular-nums text-stone-500">
                          {g.end_date ?? "—"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                    Overdue tasks
                  </p>
                  <ul className="mt-2 space-y-2">
                    {data.upcoming_deadlines.overdue_tasks.length === 0 && (
                      <li className="text-sm text-stone-400">No overdue tasks.</li>
                    )}
                    {data.upcoming_deadlines.overdue_tasks.slice(0, 4).map((t) => (
                      <li key={t.id} className="flex items-center justify-between gap-2 text-sm">
                        <span className="truncate">{t.title}</span>
                        <span className="shrink-0 tabular-nums text-rose-600 dark:text-rose-400">
                          {t.due_date ?? "—"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>
          </div>

          <Card>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Latest reports</CardTitle>
                <CardDescription>Recently updated narrative packages.</CardDescription>
              </div>
              <Link href="/app/reports">
                <Button size="sm" variant="secondary">
                  Manage reports
                </Button>
              </Link>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
                  <tr>
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Type</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {data.latest_reports.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-6">
                        <EmptyState
                          title="No reports yet"
                          description="Build a donor pack or generate an executive brief."
                          actionLabel="Go to reports"
                          actionHref="/app/reports"
                        />
                      </td>
                    </tr>
                  )}
                  {data.latest_reports.map((r) => (
                    <tr
                      key={r.id}
                      className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                    >
                      <td className="py-3 font-medium">{r.name}</td>
                      <td className="py-3 capitalize text-stone-500">
                        {r.report_type.replaceAll("_", " ")}
                      </td>
                      <td className="py-3">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="py-3 tabular-nums text-stone-500">
                        {r.updated_at
                          ? new Date(r.updated_at).toLocaleDateString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div>
            <Tabs items={DETAIL_TABS} active={tab} onChange={setTab} />
            <div className="mt-4">
              {tab === "portfolio" && (
                <PortfolioPanel loading={portfolio.isLoading} data={portfolio.data} />
              )}
              {tab === "compliance" && (
                <CompliancePanel loading={compliance.isLoading} data={compliance.data} />
              )}
              {tab === "impact" && (
                <ImpactPanel loading={impact.isLoading} data={impact.data} />
              )}
              {tab === "risks" && <RisksPanel loading={risks.isLoading} data={risks.data} />}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function PortfolioPanel({
  loading,
  data,
}: {
  loading: boolean;
  data: Awaited<ReturnType<typeof api.executivePortfolio>> | undefined;
}) {
  if (loading) return <p className="text-sm text-stone-400">Loading portfolio…</p>;
  if (!data) return null;

  const bars = data.charts.indicator_progress_bar ?? [];
  const budget = data.charts.budget_utilization ?? [];
  const budgetTotal = budget.reduce((s, b) => s + (b.value || 0), 0);
  const gender = data.charts.gender_donut ?? [];
  const genderTotal = gender.reduce((s, g) => s + (g.value || 0), 0);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardTitle>Indicator progress</CardTitle>
        <CardDescription>Top indicators toward target.</CardDescription>
        <ul className="mt-4 space-y-3">
          {bars.length === 0 && (
            <li className="text-sm text-stone-400">No indicator data yet.</li>
          )}
          {bars.map((b, i) => (
            <li key={i}>
              <div className="mb-1 flex justify-between gap-2 text-sm">
                <span className="truncate">{b.label}</span>
                <span className="tabular-nums text-stone-500">{formatPct(b.value)}</span>
              </div>
              <ProgressBar value={b.value} />
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <CardTitle>Budget utilization</CardTitle>
        <CardDescription>
          Burn {formatPct(data.efficiency.budget_utilization_pct)} · Cost / beneficiary{" "}
          {formatNum(data.efficiency.cost_per_beneficiary, 2)}
        </CardDescription>
        <ul className="mt-4 space-y-3">
          {budget.map((b, i) => (
            <li key={i}>
              <div className="mb-1 flex justify-between gap-2 text-sm">
                <span>{b.label}</span>
                <span className="tabular-nums text-stone-500">{formatNum(b.value, 0)}</span>
              </div>
              <ProgressBar
                value={b.value}
                max={budgetTotal || 1}
                className={i === 0 ? "bg-teal-600 dark:bg-teal-500" : "bg-stone-400"}
              />
            </li>
          ))}
        </ul>
        <div className="mt-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
            Gender distribution
          </p>
          <ul className="mt-3 space-y-2">
            {gender.map((g, i) => (
              <li key={i}>
                <div className="mb-1 flex justify-between text-sm capitalize">
                  <span>{g.label}</span>
                  <span className="tabular-nums text-stone-500">
                    {formatNum(g.value)} ({formatPct(genderTotal ? (g.value / genderTotal) * 100 : 0)})
                  </span>
                </div>
                <ProgressBar value={g.value} max={genderTotal || 1} />
              </li>
            ))}
          </ul>
        </div>
      </Card>

      <Card className="lg:col-span-2">
        <CardTitle>Program & grant snapshot</CardTitle>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiTile
            label="Activity completion"
            value={formatPct(data.program_performance.activity_completion_pct)}
          />
          <KpiTile
            label="Active grants"
            value={formatNum(data.grant_performance.active_grants)}
          />
          <KpiTile
            label="Evidence verified"
            value={formatPct(data.evidence_collection.verification_pct)}
          />
          <KpiTile
            label="Survey responses"
            value={formatNum(data.survey_completion.submitted_responses)}
          />
        </div>
      </Card>
    </div>
  );
}

function CompliancePanel({
  loading,
  data,
}: {
  loading: boolean;
  data: Awaited<ReturnType<typeof api.executiveCompliance>> | undefined;
}) {
  if (loading) return <p className="text-sm text-stone-400">Loading compliance…</p>;
  if (!data) return null;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardTitle>Compliance summary</CardTitle>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {Object.entries(data.summary).map(([k, v]) => (
            <KpiTile key={k} label={k.replaceAll("_", " ")} value={formatNum(v)} />
          ))}
        </div>
      </Card>
      <Card>
        <CardTitle>Recommended actions</CardTitle>
        <ul className="mt-4 space-y-3">
          {data.recommendations.length === 0 && (
            <EmptyState title="All clear" description="No compliance actions queued." />
          )}
          {data.recommendations.map((r, i) => (
            <li
              key={i}
              className="rounded-xl border border-stone-100 px-3 py-3 dark:border-stone-800"
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    SEVERITY_TONE[r.severity] ?? SEVERITY_TONE.low,
                  )}
                />
                <p className="text-sm font-medium">{r.action}</p>
              </div>
              <p className="mt-1 text-xs text-stone-500">{r.why}</p>
              {r.href ? (
                <Link
                  href={r.href}
                  className="mt-2 inline-flex text-xs font-medium text-teal-700 dark:text-teal-300"
                >
                  Open
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      </Card>
      <Card className="lg:col-span-2">
        <CardTitle>Open issues</CardTitle>
        <ul className="mt-4 divide-y divide-stone-100 dark:divide-stone-900">
          {data.issues.length === 0 && (
            <li className="py-4 text-sm text-stone-400">No open compliance issues.</li>
          )}
          {data.issues.map((issue, i) => (
            <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
              <div>
                <p className="font-medium">{issue.title}</p>
                <p className="text-xs capitalize text-stone-500">
                  {issue.category.replaceAll("_", " ")}
                  {issue.detail ? ` · ${issue.detail}` : ""}
                </p>
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">
                {issue.severity}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function ImpactPanel({
  loading,
  data,
}: {
  loading: boolean;
  data: Awaited<ReturnType<typeof api.executiveImpact>> | undefined;
}) {
  if (loading) return <p className="text-sm text-stone-400">Loading impact…</p>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Beneficiary reach" value={formatNum(data.beneficiary_reach)} />
        <KpiTile
          label="Indicators on track"
          value={`${formatNum(data.indicators_on_track)} / ${formatNum(data.indicators_total)}`}
        />
        <KpiTile
          label="Program efficiency"
          value={formatPct(data.program_efficiency_pct)}
        />
        <KpiTile
          label="Cost / beneficiary"
          value={formatNum(data.cost_per_beneficiary, 2)}
        />
      </div>
      <Card>
        <CardTitle>Indicator variances</CardTitle>
        <CardDescription>Actual vs target for tracked results.</CardDescription>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-2 font-medium">Indicator</th>
                <th className="pb-2 font-medium">Target</th>
                <th className="pb-2 font-medium">Actual</th>
                <th className="pb-2 font-medium">Variance</th>
                <th className="pb-2 font-medium">Progress</th>
              </tr>
            </thead>
            <tbody>
              {data.variances.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 text-stone-400">
                    No variance data.
                  </td>
                </tr>
              )}
              {data.variances.slice(0, 15).map((row, i) => (
                <tr
                  key={row.id ?? i}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-2.5 font-medium">{row.name}</td>
                  <td className="py-2.5 tabular-nums">{formatNum(row.target, 1)}</td>
                  <td className="py-2.5 tabular-nums">{formatNum(row.actual, 1)}</td>
                  <td className="py-2.5 tabular-nums">{formatNum(row.variance, 1)}</td>
                  <td className="py-2.5 min-w-[120px]">
                    <ProgressBar value={row.progress_pct ?? 0} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function RisksPanel({
  loading,
  data,
}: {
  loading: boolean;
  data: Awaited<ReturnType<typeof api.executiveRisks>> | undefined;
}) {
  if (loading) return <p className="text-sm text-stone-400">Loading risks…</p>;
  if (!data) return null;

  const sevEntries = Object.entries(data.by_severity);
  const sevMax = Math.max(1, ...sevEntries.map(([, n]) => n));

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
      <Card>
        <CardTitle>By severity</CardTitle>
        <ul className="mt-4 space-y-3">
          {sevEntries.length === 0 && (
            <li className="text-sm text-stone-400">No risks scored.</li>
          )}
          {sevEntries.map(([sev, n]) => (
            <li key={sev}>
              <div className="mb-1 flex justify-between text-sm capitalize">
                <span>{sev}</span>
                <span className="tabular-nums">{n}</span>
              </div>
              <ProgressBar
                value={n}
                max={sevMax}
                className={cn(
                  sev === "critical" || sev === "high"
                    ? "bg-rose-500"
                    : sev === "medium"
                      ? "bg-amber-500"
                      : "bg-stone-400",
                )}
              />
            </li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-stone-500">{data.total} total signals</p>
      </Card>
      <Card>
        <CardTitle>Risk register</CardTitle>
        <ul className="mt-4 space-y-3">
          {data.items.length === 0 && (
            <EmptyState title="No active risks" description="Risk scan returned an empty set." />
          )}
          {data.items.map((r, i) => (
            <li
              key={i}
              className="rounded-xl border border-stone-100 px-3 py-3 dark:border-stone-800"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    SEVERITY_TONE[r.severity ?? "low"] ?? SEVERITY_TONE.low,
                  )}
                />
                <p className="font-medium text-stone-900 dark:text-stone-100">
                  {r.title ?? "Risk"}
                </p>
                <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">
                  {r.severity}
                </span>
              </div>
              <p className="mt-1 text-sm text-stone-500">{r.reason ?? r.summary}</p>
              <p className="mt-2 text-xs text-stone-600 dark:text-stone-400">
                <span className="font-medium">Action:</span> {r.suggested_action}
                {r.responsible_role ? ` · Owner: ${r.responsible_role}` : ""}
                {r.recommended_deadline_days
                  ? ` · Within ${r.recommended_deadline_days}d`
                  : ""}
              </p>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
