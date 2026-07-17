"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

function meter(label: string, used: number, limit?: number | null) {
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="text-stone-500">{label}</span>
        <span className="font-medium">
          {used}
          {limit != null ? ` / ${limit}` : " · unlimited"}
        </span>
      </div>
      {limit != null && (
        <div className="mt-1 h-2 overflow-hidden rounded-full bg-stone-100">
          <div className="h-full rounded-full bg-teal-600" style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}

function BillingInner() {
  const qc = useQueryClient();
  const search = useSearchParams();
  const [period, setPeriod] = useState<"monthly" | "annual">("monthly");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState<string | null>(null);

  const plans = useQuery({ queryKey: ["billing-plans"], queryFn: () => api.listBillingPlans() });
  const sub = useQuery({ queryKey: ["subscription"], queryFn: () => api.getSubscription() });
  const features = useQuery({ queryKey: ["features"], queryFn: () => api.getFeatures() });
  const usage = useQuery({ queryKey: ["billing-usage"], queryFn: () => api.getBillingUsage() });
  const invoices = useQuery({
    queryKey: ["billing-invoices"],
    queryFn: () => api.listBillingInvoices(),
  });

  useEffect(() => {
    const reference = search.get("reference") || search.get("trxref");
    if (!reference) return;
    let cancelled = false;
    (async () => {
      try {
        await api.verifyPaystack(reference);
        if (!cancelled) {
          setNotice("Payment confirmed — your plan is updated.");
          setError(null);
          await qc.invalidateQueries({ queryKey: ["subscription"] });
          await qc.invalidateQueries({ queryKey: ["features"] });
          await qc.invalidateQueries({ queryKey: ["billing-usage"] });
          await qc.invalidateQueries({ queryKey: ["billing-invoices"] });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not verify payment");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [search, qc]);

  const change = useMutation({
    mutationFn: (plan_code: string) =>
      api.changeSubscription({ plan_code, billing_period: period }),
    onSuccess: async (result) => {
      setError(null);
      setUpgradeOpen(null);
      if (result && typeof result === "object" && "authorization_url" in result) {
        const url = (result as { authorization_url?: string | null }).authorization_url;
        if (url) {
          setNotice("Redirecting to Paystack…");
          window.location.href = url;
          return;
        }
      }
      setNotice("Plan updated.");
      await qc.invalidateQueries({ queryKey: ["subscription"] });
      await qc.invalidateQueries({ queryKey: ["features"] });
      await qc.invalidateQueries({ queryKey: ["billing-usage"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const cancel = useMutation({
    mutationFn: () => api.cancelSubscription(true),
    onSuccess: async () => {
      setNotice("Cancellation scheduled at period end.");
      await qc.invalidateQueries({ queryKey: ["subscription"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const days = sub.data?.days_remaining;

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Billing</h1>
          <p className="mt-2 text-stone-500">
            Manage your plan, usage, invoices, and Paystack renewals.
          </p>
        </div>
        <Link href="/pricing" className="text-sm font-medium text-teal-800 hover:underline">
          View public pricing
        </Link>
      </div>

      {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
      {notice && (
        <p className="rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-800">{notice}</p>
      )}

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Current plan</CardTitle>
            <CardDescription>
              {sub.data?.plan?.name ?? "Loading…"} · {sub.data?.status} · {sub.data?.provider}
            </CardDescription>
          </div>
          {sub.data?.status === "trialing" && days != null && (
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
              {days} day{days === 1 ? "" : "s"} left in trial
            </span>
          )}
        </div>
        {sub.data && (
          <dl className="mt-4 grid gap-3 sm:grid-cols-4">
            <div>
              <dt className="text-xs uppercase text-stone-500">Seats</dt>
              <dd className="font-medium">{sub.data.seats}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-stone-500">Period</dt>
              <dd className="font-medium">{sub.data.billing_period}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-stone-500">Renews</dt>
              <dd className="font-medium">
                {sub.data.current_period_end
                  ? new Date(sub.data.current_period_end).toLocaleDateString()
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-stone-500">Projected renewal</dt>
              <dd className="font-medium">
                {usage.data
                  ? `${usage.data.projected_renewal.currency} ${usage.data.projected_renewal.amount.toLocaleString()}`
                  : "—"}
              </dd>
            </div>
          </dl>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            variant={period === "monthly" ? "default" : "secondary"}
            onClick={() => setPeriod("monthly")}
          >
            Monthly
          </Button>
          <Button
            variant={period === "annual" ? "default" : "secondary"}
            onClick={() => setPeriod("annual")}
          >
            Annual
          </Button>
          <Button
            variant="secondary"
            disabled={cancel.isPending || sub.data?.cancel_at_period_end}
            onClick={() => cancel.mutate()}
          >
            {sub.data?.cancel_at_period_end ? "Cancel scheduled" : "Cancel at period end"}
          </Button>
        </div>
      </Card>

      {usage.data && (
        <Card>
          <CardTitle>Usage</CardTitle>
          <CardDescription>Limits from your current plan.</CardDescription>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {meter("Users", usage.data.users.used, usage.data.users.limit)}
            {meter("Projects", usage.data.projects.used, usage.data.projects.limit)}
            {meter("Storage (GB)", usage.data.storage_gb.used, usage.data.storage_gb.limit)}
            {meter("AI credits", usage.data.ai_credits.used, usage.data.ai_credits.limit)}
            {meter("API calls", usage.data.api_calls.used, usage.data.api_calls.limit)}
          </div>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {(plans.data?.items ?? []).map((plan) => {
          const price = period === "annual" ? plan.price_annual : plan.price_monthly;
          const active = sub.data?.plan?.code === plan.code;
          const isFree = Number(price || 0) <= 0 || plan.code === "free";
          const contact = plan.contact_sales || plan.code === "government";
          return (
            <Card
              key={plan.id}
              className={
                active
                  ? "ring-2 ring-teal-600"
                  : plan.recommended
                    ? "ring-1 ring-[#16324F]/30"
                    : undefined
              }
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>{plan.name}</CardTitle>
                  <CardDescription>{plan.description ?? plan.tier}</CardDescription>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {active && <StatusBadge status="active" />}
                  {plan.recommended && (
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-[#2F5D3A]">
                      Recommended
                    </span>
                  )}
                </div>
              </div>
              <p className="mt-4 font-display text-3xl font-semibold">
                {contact ? (
                  "Contact sales"
                ) : isFree ? (
                  "Free trial"
                ) : (
                  <>
                    {plan.currency} {Number(price).toLocaleString()}
                    <span className="text-sm font-normal text-stone-500">
                      /{period === "annual" ? "yr" : "mo"}
                    </span>
                  </>
                )}
              </p>
              <ul className="mt-3 space-y-1 text-sm text-stone-600 dark:text-stone-400">
                <li>{plan.seat_limit ? `${plan.seat_limit} seats` : "Unlimited seats"}</li>
                <li>
                  {plan.max_projects == null
                    ? "Unlimited projects"
                    : `${plan.max_projects} projects`}
                </li>
                <li>{plan.storage_gb ? `${plan.storage_gb} GB storage` : "Custom storage"}</li>
              </ul>
              {contact ? (
                <a
                  href="mailto:chris@impactflow.space"
                  className="mt-4 inline-flex h-10 items-center justify-center rounded-xl border border-stone-300 px-4 text-sm font-medium"
                >
                  Contact sales
                </a>
              ) : (
                <Button
                  className="mt-4"
                  disabled={active || change.isPending}
                  onClick={() => setUpgradeOpen(plan.code)}
                >
                  {active ? "Current plan" : isFree ? "Switch to trial" : "Upgrade"}
                </Button>
              )}
            </Card>
          );
        })}
      </div>

      <Card>
        <CardTitle>Invoices & receipts</CardTitle>
        <CardDescription>Payment history from Paystack activations and renewals.</CardDescription>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-stone-500">
                <th className="py-2 pr-3">Invoice</th>
                <th className="py-2 pr-3">Amount</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {(invoices.data?.items ?? []).length === 0 && (
                <tr>
                  <td colSpan={4} className="py-4 text-stone-500">
                    No invoices yet.
                  </td>
                </tr>
              )}
              {(invoices.data?.items ?? []).map((inv) => (
                <tr key={inv.id} className="border-b border-stone-100">
                  <td className="py-2 pr-3 font-medium">{inv.number}</td>
                  <td className="py-2 pr-3">
                    {inv.currency} {Number(inv.amount).toLocaleString()}
                  </td>
                  <td className="py-2 pr-3">
                    <StatusBadge status={inv.status} />
                  </td>
                  <td className="py-2">
                    {inv.paid_at || inv.created_at
                      ? new Date(inv.paid_at || inv.created_at || "").toLocaleDateString()
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardTitle>Feature flags</CardTitle>
        <CardDescription>Resolved for this organization from plan + overrides.</CardDescription>
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(features.data?.features ?? {}).map(([code, on]) => (
            <span
              key={code}
              className={`rounded-lg px-2.5 py-1 text-xs font-medium ${
                on
                  ? "bg-teal-100 text-teal-900 dark:bg-teal-900/40 dark:text-teal-100"
                  : "bg-stone-100 text-stone-500 dark:bg-stone-900"
              }`}
            >
              {code}
            </span>
          ))}
        </div>
      </Card>

      {upgradeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="font-display text-xl font-semibold">Confirm plan change</h2>
            <p className="mt-2 text-sm text-stone-600">
              You are switching to <strong>{upgradeOpen}</strong> ({period}). Paid plans open
              Paystack checkout; payment is verified on the server before activation.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setUpgradeOpen(null)}>
                Cancel
              </Button>
              <Button disabled={change.isPending} onClick={() => change.mutate(upgradeOpen)}>
                {change.isPending ? "Working…" : "Continue"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<p className="p-6 text-stone-500">Loading billing…</p>}>
      <BillingInner />
    </Suspense>
  );
}
