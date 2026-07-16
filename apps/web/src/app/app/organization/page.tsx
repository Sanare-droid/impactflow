"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

export default function OrganizationPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["organization"],
    queryFn: () => api.currentOrganization(),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Organization
        </h1>
        <p className="mt-2 text-stone-500">Tenant profile and workspace configuration.</p>
      </div>

      <Card>
        <CardTitle>{isLoading ? "Loading…" : data?.name}</CardTitle>
        <CardDescription>Multi-tenant root for all project data.</CardDescription>
        {error && <p className="mt-4 text-sm text-rose-600">{(error as Error).message}</p>}
        {data && (
          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            {[
              ["Slug", data.slug],
              ["Type", data.organization_type],
              ["Country", data.country_code ?? "—"],
              ["Timezone", data.timezone],
              ["Locale", data.locale],
              ["Verified", data.is_verified ? "Yes" : "No"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-stone-50 p-4 dark:bg-stone-900">
                <dt className="text-xs uppercase tracking-wide text-stone-500">{label}</dt>
                <dd className="mt-1 font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </Card>
    </div>
  );
}
