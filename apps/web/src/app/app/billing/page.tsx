"use client";

import { Suspense, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

function BillingInner() {
  const qc = useQueryClient();
  const search = useSearchParams();
  const [period, setPeriod] = useState<"monthly" | "annual">("monthly");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const plans = useQuery({ queryKey: ["billing-plans"], queryFn: () => api.listBillingPlans() });
  const sub = useQuery({ queryKey: ["subscription"], queryFn: () => api.getSubscription() });
  const features = useQuery({ queryKey: ["features"], queryFn: () => api.getFeatures() });

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
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Subscription</h1>
        <p className="mt-2 text-stone-500">
          Start on Free. Upgrade anytime — paid plans checkout via Paystack when configured.
        </p>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {notice && <p className="text-sm text-teal-700">{notice}</p>}

      <Card>
        <CardTitle>Current plan</CardTitle>
        <CardDescription>
          {sub.data?.plan?.name ?? "Loading…"} · {sub.data?.status} · {sub.data?.provider}
        </CardDescription>
        {sub.data && (
          <dl className="mt-4 grid gap-3 sm:grid-cols-3">
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
          </dl>
        )}
        <div className="mt-4 flex gap-2">
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
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {(plans.data?.items ?? []).map((plan) => {
          const price = period === "annual" ? plan.price_annual : plan.price_monthly;
          const active = sub.data?.plan?.code === plan.code;
          const isFree = Number(price) <= 0 || plan.code === "free";
          return (
            <Card key={plan.id} className={active ? "ring-2 ring-teal-600" : undefined}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>{plan.name}</CardTitle>
                  <CardDescription>{plan.description ?? plan.tier}</CardDescription>
                </div>
                {active && <StatusBadge status="active" />}
              </div>
              <p className="mt-4 font-display text-3xl font-semibold">
                {isFree ? (
                  "Free"
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
                <li>{plan.storage_gb ? `${plan.storage_gb} GB storage` : "Custom storage"}</li>
                <li>
                  {plan.features.includes("*")
                    ? "All platform features"
                    : plan.features.slice(0, 4).join(", ")}
                </li>
              </ul>
              <Button
                className="mt-4"
                disabled={active || change.isPending || plan.code === "government"}
                onClick={() => change.mutate(plan.code)}
              >
                {active
                  ? "Current plan"
                  : isFree
                    ? "Switch to Free"
                    : "Upgrade with Paystack"}
              </Button>
            </Card>
          );
        })}
      </div>

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
