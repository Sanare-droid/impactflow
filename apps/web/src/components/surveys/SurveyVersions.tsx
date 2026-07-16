"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type Survey } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function SurveyVersions({ survey }: { survey: Survey }) {
  const { data, isLoading } = useQuery({
    queryKey: ["survey-versions", survey.id],
    queryFn: () => api.listSurveyVersions(survey.id),
  });

  return (
    <Card>
      <CardTitle>Version history</CardTitle>
      <CardDescription>Every schema save creates an immutable snapshot.</CardDescription>
      <div className="mt-4 space-y-2">
        {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
        {data?.map((v) => (
          <div
            key={v.id}
            className={cn(
              "rounded-lg border border-stone-100 px-3 py-2.5 text-sm dark:border-stone-900",
              v.version === survey.current_version && "border-teal-300 bg-teal-50/50 dark:border-teal-800 dark:bg-teal-950/30",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-stone-800 dark:text-stone-100">
                v{v.version}
                {v.version === survey.current_version && (
                  <span className="ml-2 text-xs font-normal text-teal-700 dark:text-teal-300">current</span>
                )}
              </span>
              <span className="text-xs text-stone-400">
                {new Date(v.created_at).toLocaleDateString()}
              </span>
            </div>
            {v.changelog && <p className="mt-1 text-xs text-stone-500">{v.changelog}</p>}
            <p className="mt-1 text-xs text-stone-400">
              {v.published_at ? `Published ${new Date(v.published_at).toLocaleString()}` : "Not published"}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
