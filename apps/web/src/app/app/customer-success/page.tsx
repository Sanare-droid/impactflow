"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

export default function CustomerSuccessPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["customer-success"],
    queryFn: () => api.getCustomerSuccess(),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Customer success</h1>
        <p className="mt-2 text-stone-500">
          Adoption, health score, and recommended actions for this organization.
        </p>
      </div>

      {error && <p className="text-sm text-rose-600">{(error as Error).message}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Health", data ? `${data.health_score}` : "—"],
          ["Adoption", data ? `${data.adoption_pct}%` : "—"],
          ["Active users", data?.active_users ?? "—"],
          ["Integrations", data?.integrations ?? "—"],
        ].map(([label, value]) => (
          <Card key={label}>
            <CardDescription>{label}</CardDescription>
            <CardTitle className="mt-2 font-display text-3xl">{isLoading ? "…" : value}</CardTitle>
          </Card>
        ))}
      </div>

      <Card>
        <CardTitle>Recommendations</CardTitle>
        <CardDescription>Privacy-respecting guidance to improve activation.</CardDescription>
        <ul className="mt-4 space-y-3">
          {(data?.recommendations ?? []).length === 0 && (
            <li className="text-sm text-stone-500">No open recommendations — strong adoption.</li>
          )}
          {(data?.recommendations ?? []).map((r) => (
            <li
              key={r.href + r.action}
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-200 px-4 py-3 dark:border-stone-800"
            >
              <div>
                <div className="font-medium">{r.action}</div>
                <div className="text-xs text-stone-500">{r.why}</div>
              </div>
              <Link
                href={r.href}
                className="inline-flex h-8 items-center rounded-md bg-stone-100 px-3 text-xs font-medium text-stone-900 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-100"
              >
                Open
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
