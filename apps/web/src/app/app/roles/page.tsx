"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

export default function RolesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api.roles(),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Roles</h1>
        <p className="mt-2 text-stone-500">
          System roles provisioned per organization with granular permissions.
        </p>
      </div>

      {error && (
        <Card className="border-rose-200 text-rose-700">
          {(error as Error).message}
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {isLoading && <Card>Loading roles…</Card>}
        {data?.map((role) => (
          <Card key={role.id}>
            <CardTitle>{role.name}</CardTitle>
            <CardDescription>{role.description}</CardDescription>
            <div className="mt-4 flex flex-wrap gap-2">
              {role.permissions.slice(0, 8).map((p) => (
                <span
                  key={p}
                  className="rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-700 dark:bg-stone-900 dark:text-stone-300"
                >
                  {p}
                </span>
              ))}
              {role.permissions.length > 8 && (
                <span className="text-xs text-stone-500">
                  +{role.permissions.length - 8} more
                </span>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
