"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

export default function AuditPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/audit-logs`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("if_access_token")}`,
            "X-Organization-Id": localStorage.getItem("if_organization_id") ?? "",
          },
        },
      );
      if (!res.ok) throw new Error("Unable to load audit logs");
      return res.json() as Promise<{
        items: Array<{
          id: string;
          action: string;
          resource_type: string;
          actor_email?: string;
          description?: string;
          created_at: string;
          status: string;
        }>;
      }>;
    },
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Audit logs
        </h1>
        <p className="mt-2 text-stone-500">
          Immutable trail of authentication and administration events.
        </p>
      </div>

      <Card>
        <CardTitle>Recent activity</CardTitle>
        <CardDescription>Events are organization-scoped for compliance.</CardDescription>
        {error && <p className="mt-4 text-sm text-rose-600">{(error as Error).message}</p>}
        <div className="mt-5 space-y-3">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {data?.items.map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-800"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{item.action}</p>
                <span className="text-xs text-stone-500">
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </div>
              <p className="mt-1 text-sm text-stone-500">
                {item.description || `${item.resource_type}`} · {item.actor_email || "system"}
              </p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
