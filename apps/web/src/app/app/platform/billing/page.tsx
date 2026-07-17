"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-stone-200/80 bg-white/70 p-4">
      <p className="text-xs uppercase tracking-wide text-stone-500">{label}</p>
      <p className="font-display mt-1 text-2xl font-semibold text-stone-900">{value}</p>
    </div>
  );
}

export default function PlatformBillingPage() {
  const qc = useQueryClient();
  const [orgId, setOrgId] = useState("");
  const [planCode, setPlanCode] = useState("government");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const analytics = useQuery({
    queryKey: ["platform-billing-analytics"],
    queryFn: () => api.getPlatformBillingAnalytics(),
    retry: false,
  });

  const assign = useMutation({
    mutationFn: () =>
      api.assignPlatformPlan({
        organization_id: orgId.trim(),
        plan_code: planCode,
        billing_period: "monthly",
      }),
    onSuccess: async () => {
      setNotice(`Assigned ${planCode} successfully.`);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["platform-billing-analytics"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (analytics.isError) {
    return (
      <div className="p-6">
        <h1 className="font-display text-2xl font-semibold">Platform billing</h1>
        <p className="mt-2 text-sm text-rose-700">
          Platform admin access required to view revenue analytics.
        </p>
      </div>
    );
  }

  const a = analytics.data;

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Platform billing</h1>
        <p className="mt-2 text-stone-500">
          Super-admin MRR, trials, and manual Government / Enterprise assignments.
        </p>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {notice && <p className="text-sm text-teal-700">{notice}</p>}

      {a && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="MRR" value={`${a.currency} ${a.mrr.toLocaleString()}`} />
          <Metric label="ARR" value={`${a.currency} ${a.arr.toLocaleString()}`} />
          <Metric label="Revenue" value={`${a.currency} ${a.revenue.toLocaleString()}`} />
          <Metric label="Active orgs" value={a.active_organizations} />
          <Metric label="Trials" value={a.trials} />
          <Metric label="Conversions" value={a.conversions} />
          <Metric label="Grace" value={a.grace_period_accounts} />
          <Metric label="Expired" value={a.expired_accounts} />
          <Metric label="Government" value={a.government_accounts} />
          <Metric label="Enterprise" value={a.enterprise_contracts} />
          <Metric label="Popular plan" value={a.most_popular_plan || "—"} />
          <Metric
            label="ARPO"
            value={`${a.currency} ${a.average_revenue_per_organization.toLocaleString()}`}
          />
        </div>
      )}

      <Card>
        <CardTitle>Assign manual plan</CardTitle>
        <CardDescription>
          Assign Government or Enterprise contracts without Paystack checkout.
        </CardDescription>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Input
            placeholder="Organization UUID"
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
          />
          <select
            className="h-10 rounded-xl border border-stone-200 bg-white px-3 text-sm"
            value={planCode}
            onChange={(e) => setPlanCode(e.target.value)}
          >
            <option value="government">Government</option>
            <option value="enterprise">Enterprise</option>
            <option value="professional">Professional</option>
            <option value="starter">Starter</option>
            <option value="free">Free Trial</option>
          </select>
          <Button
            disabled={!orgId.trim() || assign.isPending}
            onClick={() => assign.mutate()}
          >
            Assign plan
          </Button>
        </div>
      </Card>
    </div>
  );
}
